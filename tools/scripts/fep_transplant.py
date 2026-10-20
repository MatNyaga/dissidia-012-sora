"""Copy a leaf's node tree (and the MDL / ANM / TEX data it draws) from one fighter's FEP into another's -- notes/
kh2-effects.md "Lightning's thunder in Sora". Library for spot33_lightningfx.py; works on fep.Fep objects.

Model (fep.py): every offset target is a Blob, offsets are symbolic (blob, pos, target). A tree's data (tree header,
root/node lists, nodes, tracks, init data, param blocks, t24/t28/t2c/t30 lists) is the set of blobs reachable from
the tree blob; resources are referenced from nodes by INDEX (node components 0x0b/0x14 MDL, 0x0a/0x15 ANM, 0x6a TEX),
never by pointer. So a transplant = copy that blob subgraph, remap the resource indexes inside the copied nodes, make
the destination's tree-list entry point at the copy, and drop the old tree's blobs (Sora's trees share no blobs --
checked; the loader relocates every field once, so blobs must never be shared between trees).
Size: the writer re-lays blobs, so the FEP grows/shrinks by the difference; callers keep the total constant with
gut() (replace dead trees by empty ones) + pad() (an unreferenced trailing blob).
"""
import struct

import fep as F


def ptr_index(f):
    out = {}
    for p in f.ptrs:
        out.setdefault(id(p[0]), []).append(p)
    return out


def subgraph(f, root):
    """-> list of blobs reachable from `root` (root first)"""
    idx = ptr_index(f)
    seen, order, st = {id(root)}, [root], [root]
    while st:
        b = st.pop()
        for p in idx.get(id(b), []):
            t = p[2]
            if id(t) not in seen:
                seen.add(id(t))
                order.append(t)
                st.append(t)
    return order


def tree_slot(f, tree_index):
    """-> the ptr record of tree-list entry `tree_index`"""
    lst = f.target(f.head(), 0x2c)
    return next(p for p in f.ptrs if p[0] is lst and p[1] == 4 * tree_index)


def leaf_tree_index(d, leaf_index):
    lf = F.u32(d, F.u32(d, 0x28) + 4 * leaf_index)
    return F.u16(d, lf + 4)


def blob_at(f, off):
    """-> (blob, pos) containing original file offset `off`"""
    for b in f.blobs:
        if b.off is not None and b.off <= off < b.off + len(b.data):
            return b, off - b.off
    raise KeyError(hex(off))


def copy_tree(dst, src, src_d, src_leaf, dst_leaf, dst_d, res_map):
    """replace dst leaf `dst_leaf`'s tree by a copy of src leaf `src_leaf`'s tree. res_map = {'MDL': {i: j}, 'ANM':
    {...}, 'TEX': {...}} remaps the resource indexes in the copied nodes (unmapped index -> KeyError). -> (removed B,
    added B)"""
    s_slot = tree_slot(src, leaf_tree_index(src_d, src_leaf))
    d_slot = tree_slot(dst, leaf_tree_index(dst_d, dst_leaf))
    s_blobs = subgraph(src, s_slot[2])
    old = subgraph(dst, d_slot[2])
    # resource-index fields inside the source nodes: (source blob, pos) -> new u16
    patch = {}
    tree_off = s_slot[2].off
    for k in range(F.u16(src_d, tree_off + 0x12)):
        nl = F.u32(src_d, tree_off + 0x20)
        nd = F.u32(src_d, nl + 4 * k)
        if not nd:
            continue
        for c, _, o in F.node_components(src_d, nd):
            if c in F.COMP_RES and o is not None:
                kind = F.COMP_RES[c]
                b, pos = blob_at(src, o)
                patch[(id(b), pos)] = res_map[kind][F.u16(src_d, o)]
    new = {}
    for b in s_blobs:
        nb = F.Blob(None, bytes(b.data), b.align)
        nb.kinds = set(b.kinds)
        new[id(b)] = nb
    for (bid, pos), v in patch.items():
        struct.pack_into('<H', new[bid].data, pos, v)
    sidx = ptr_index(src)
    old_ids = {id(b) for b in old}
    # remove the old tree's blobs + pointer records, insert the copy where the old tree was
    at = dst.blobs.index(old[0])
    dst.blobs = [b for b in dst.blobs if id(b) not in old_ids]
    dst.ptrs = [p for p in dst.ptrs if id(p[0]) not in old_ids]
    for i, b in enumerate(s_blobs):
        dst.blobs.insert(at + i, new[id(b)])
    for b in s_blobs:
        for p in sidx.get(id(b), []):
            dst.ptrs.append([new[id(b)], p[1], new[id(p[2])], p[3]])
    d_slot[2] = new[id(s_blobs[0])]
    assert not [p for p in dst.ptrs if id(p[2]) in old_ids], 'old tree blobs still referenced'
    return sum(len(b.data) for b in old), sum(len(b.data) for b in s_blobs)


def put_resource(dst, kind, slot, data, key=None, size=None):
    """overwrite dst `kind` slot's data blob with `data` (record +8 = size or len(data)); key -> record +4 (and data
    self key for own data)"""
    rec, blob = dst.resources(kind)[slot]
    if key is not None:
        struct.pack_into('<I', rec.data, 4, key)
    blob.data[:] = bytes(data) + b'\0' * (-len(data) % F.DATA_ALIGN)
    struct.pack_into('<I', rec.data, 8, len(data) if size is None else size)


def gut(dst, dst_d, leaf_index, empty_src, empty_src_d, empty_leaf):
    """replace a (dead) leaf's tree by a copy of an EMPTY tree (0 nodes) from another FEP -> bytes saved"""
    rm, add = copy_tree(dst, empty_src, empty_src_d, empty_leaf, leaf_index, dst_d, {'MDL': {}, 'ANM': {}, 'TEX': {}})
    return rm - add


def pad_to(dst, size):
    """append an unreferenced zero blob so the written FEP is exactly `size` bytes (must not be bigger already)"""
    cur = len(dst.write())
    assert cur <= size, 'FEP is %d B, %d over the budget' % (cur, cur - size)
    if cur < size:
        dst.blobs.append(F.Blob(None, bytes(size - cur), 4))
    assert len(dst.write()) == size
