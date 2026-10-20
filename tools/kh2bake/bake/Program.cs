// Bake KH2 motions (mset) to per-frame bone matrices with OpenKH's KH2 animation emulator (IK/constraints included).
// Usage: bake MDLX MSET OUT_DIR [list | all | INDEX ...]   (env STEP=0.5 → record every half frame = half speed;
//        env SPEED="0.5:1,1:0.4" → normal speed for the first 50% of the motion, then 0.4× to the end)
// Output per ANB entry: OUT_DIR/<index>_<name>.bin = header (int bones, int frames, float fps, float frameEnd,
// float frameLoop) + frames x bones x 16 floats (System.Numerics row-major, model space, KH2 units = cm, Y up).
using System; using System.IO; using System.Linq; using OpenKh.Kh2; using OpenKh.Kh2Anim.Mset; using OpenKh.Kh2Anim.Mset.Interfaces;
var mdlx = File.ReadAllBytes(args[0]);
var mset = Bar.Read(File.OpenRead(args[1]));
var outDir = args[2]; Directory.CreateDirectory(outDir);
var mode = args.Length > 3 ? args[3] : "list";
var step = double.Parse(Environment.GetEnvironmentVariable("STEP") ?? "1", System.Globalization.CultureInfo.InvariantCulture);
var speedSpec = Environment.GetEnvironmentVariable("SPEED");
var wanted = args.Skip(3).Where(a => int.TryParse(a, out _)).Select(int.Parse).ToHashSet();
for (int i = 0; i < mset.Count; i++) {
  var e = mset[i];
  if (e.Type != Bar.EntryType.Anb || e.Stream.Length == 0) { if (mode == "list") Console.WriteLine($"{i,4} {e.Name} {e.Type} len={e.Stream.Length}"); continue; }
  e.Stream.Position = 0;
  var anb = Bar.Read(e.Stream);
  var ai = new AnbIndir(anb);
  if (!ai.HasAnimationData) { Console.WriteLine($"{i,4} {e.Name} (no motion)"); continue; }
  IAnimMatricesProvider p;
  try { p = ai.GetAnimProvider(new MemoryStream(mdlx, false)); } catch (Exception ex) { Console.WriteLine($"{i,4} {e.Name} ERROR {ex.Message}"); continue; }
  // sample times in KH2 frames (constant STEP, or piecewise SPEED)
  var times = new System.Collections.Generic.List<double>();
  if (speedSpec == null) { for (double t = 0; t <= p.FrameEnd + 1e-6; t += step) times.Add(t); }
  else {
    var parts = speedSpec.Split(',').Select(x => x.Split(':').Select(v => double.Parse(v, System.Globalization.CultureInfo.InvariantCulture)).ToArray()).ToArray();
    for (double t = 0; t <= p.FrameEnd + 1e-6;) {
      times.Add(t);
      var sp = parts.First(pp => t <= pp[0] * p.FrameEnd + 1e-6 || pp == parts.Last())[1];
      t += sp;
    }
  }
  int frames = times.Count;
  Console.WriteLine($"{i,4} {e.Name} fps={p.FramePerSecond} end={p.FrameEnd} loop={p.FrameLoop} count={p.FrameCount} matrices={p.MatrixCount}");
  if (mode == "list" || (mode != "all" && !wanted.Contains(i))) continue;
  using var w = new BinaryWriter(File.Create(Path.Combine(outDir, speedSpec != null ? $"{i:D3}_{e.Name}_v{speedSpec.Replace(':', 'x').Replace(',', '_')}.bin" : step == 1 ? $"{i:D3}_{e.Name}.bin" : $"{i:D3}_{e.Name}_s{step.ToString(System.Globalization.CultureInfo.InvariantCulture)}.bin")));
  var first = p.ProvideMatrices2(0).Fk;
  w.Write(first.Length); w.Write(frames); w.Write(p.FramePerSecond); w.Write(p.FrameEnd); w.Write(p.FrameLoop);
  for (int f = 0; f < frames; f++) {
    p.ResetGameTimeDelta();
    var fk = p.ProvideMatrices2(60.0 / p.FramePerSecond * times[f]).Fk;
    foreach (var m in fk) { w.Write(m.M11); w.Write(m.M12); w.Write(m.M13); w.Write(m.M14); w.Write(m.M21); w.Write(m.M22); w.Write(m.M23); w.Write(m.M24);
                            w.Write(m.M31); w.Write(m.M32); w.Write(m.M33); w.Write(m.M34); w.Write(m.M41); w.Write(m.M42); w.Write(m.M43); w.Write(m.M44); }
  }
}
