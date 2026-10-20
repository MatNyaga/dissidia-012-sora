using System; using System.Linq; using System.Reflection;
var dir = args[0];
AppDomain.CurrentDomain.AssemblyResolve += (s, e) => { var p = System.IO.Path.Combine(dir, new AssemblyName(e.Name).Name + ".dll"); return System.IO.File.Exists(p) ? Assembly.LoadFrom(p) : null; };
foreach (var dll in args.Skip(1).Where(a => a.EndsWith(".dll"))) {
  var asm = Assembly.LoadFrom(System.IO.Path.Combine(dir, dll));
  Type[] types; try { types = asm.GetTypes(); } catch (ReflectionTypeLoadException ex) { types = ex.Types.Where(t => t != null).ToArray(); }
  foreach (var t in types.Where(t => args.Skip(1).Where(a => !a.EndsWith(".dll")).Any(f => t.FullName.Contains(f)))) {
    Console.WriteLine($"== {t.FullName} : {t.BaseType?.Name} [{string.Join(",", t.GetInterfaces().Select(i=>i.Name))}]");
    foreach (var m in t.GetMembers(BindingFlags.Public|BindingFlags.Instance|BindingFlags.Static|BindingFlags.DeclaredOnly))
      Console.WriteLine("   " + m.MemberType + " " + m);
  }
}
