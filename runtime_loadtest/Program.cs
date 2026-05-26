// runtime_loadtest — UiPath SDK XAML load test host.
//
// Carrega cada XAML via System.Activities.XamlIntegration usando o seam
// público UiPath.Workflow (CoreWF fork). ActivityXamlServices.Load() +
// WorkflowInspectionServices.CacheMetadata força eager type resolution +
// VB expression compile.
//
// Captura runtime errors que UiPath Studio Analyzer estático não pega:
//   - VB compile errors em Variable.Default (e.g., smart-quote “” vs "")
//   - Type resolution failures (missing assembly ref)
//   - Malformed Activity tree (broken XAML structure)
//   - Validation errors (required arg missing, type mismatch)
//
// Uso:
//   runtime_loadtest.exe <xaml_path> [<xaml_path>...]
//   runtime_loadtest.exe --stdin     # path por linha em stdin (batch mode)
//
// Output: JSON em stdout, `{"results": [LoadResult, ...]}`.
// Exit: 0 se todos OK, 1 se ≥1 failed, 2 se invalid args.
using System;
using System.Globalization;
using System.Threading;
using System.Activities;
using System.Activities.Validation;
using System.Activities.XamlIntegration;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Xaml;
using System.Xaml.Schema;

namespace SicoobUiPath.RuntimeLoadTest;

public class Program
{
    /// <summary>
    /// Shared schema context — built once after PreloadXmlnsBearingAssemblies.
    /// Reused per XAML load so reflection scan / cache reuses across files.
    /// </summary>
    private static XamlSchemaContext? _schemaContext;

    public static int Main(string[] args)
    {
        // CultureInfo invariant: XAML deserialization parses literals
        // (Double, TimeSpan, etc.) usando CurrentCulture. Em pt-BR, "0.3"
        // não é Double válido (separador é vírgula). Studio sempre usa
        // invariant culture pra XAML serialize/deserialize — replicar aqui
        // pra evitar ArgumentException("X is not a valid value for Y").
        Thread.CurrentThread.CurrentCulture = CultureInfo.InvariantCulture;
        Thread.CurrentThread.CurrentUICulture = CultureInfo.InvariantCulture;
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;

        // XAML xmlns resolution: ActivityXamlServices.Load() varre
        // AppDomain.CurrentDomain.GetAssemblies() procurando
        // XmlnsDefinitionAttribute pra mapear
        // "http://schemas.uipath.com/workflow/activities" → tipos CLR.
        // Sem pre-load, só assemblies com PackageReference direto estão
        // carregados — UiPath ship 40+ assemblies satélites c/ mappings
        // espalhados. Pre-load aqui é EAGER LOAD, não hack:
        // carregamos só UiPath.*.dll / CCS_*.dll vizinhos ao exe.
        // Sem AssemblyResolve null-sink, sem culture hack — UiPath.Workflow
        // (Public SDK) shipa satellites/resources corretamente.
        PreloadXmlnsBearingAssemblies();
        _schemaContext = BuildSchemaContext();

        if (args.Length > 0 && args[0] == "--dump-xmlns")
        {
            DumpXmlnsMappings();
            return 0;
        }

        if (args.Length > 0 && args[0] == "--dump-asm-types")
        {
            // Usage: --dump-asm-types <AsmName> [<nsPrefix>]
            var asmName = args[1];
            var prefix = args.Length > 2 ? args[2] : "";
            var asm = AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(a => a.GetName().Name == asmName);
            if (asm == null) { Console.WriteLine($"asm not loaded: {asmName}"); return 0; }
            Type[] types;
            try { types = asm.GetTypes(); }
            catch (System.Reflection.ReflectionTypeLoadException rtle) { types = rtle.Types.Where(t => t != null).ToArray()!; }
            foreach (var t in types)
            {
                if (t == null) continue;
                if (!t.IsPublic) continue;
                var fn = t.FullName ?? "";
                if (string.IsNullOrEmpty(prefix) || fn.StartsWith(prefix))
                {
                    Console.WriteLine(fn);
                }
            }
            return 0;
        }

        if (args.Length > 0 && args[0] == "--locate-type")
        {
            // Usage: --locate-type <FullTypeName>
            // For each loaded assembly, try asm.GetType(name) + asm.GetType(name, false, true) (ignoreCase)
            var fn = args[1];
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic))
            {
                Type? t;
                try { t = asm.GetType(fn, throwOnError: false); } catch { continue; }
                if (t != null)
                {
                    Console.WriteLine($"  found in {asm.GetName().Name}: {t.FullName} (loc {asm.Location})");
                }
            }
            return 0;
        }

        if (args.Length > 0 && args[0] == "--list-asms")
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies().OrderBy(a => a.GetName().Name))
            {
                var n = asm.GetName().Name ?? "";
                Console.WriteLine(n);
            }
            return 0;
        }

        if (args.Length > 0 && args[0] == "--dump-ctx-xmlns")
        {
            // Print xmlns namespaces visible to the custom SchemaContext.
            var ctx = _schemaContext!;
            foreach (var ns in ctx.GetAllXamlNamespaces())
            {
                Console.WriteLine(ns);
            }
            return 0;
        }

        if (args.Length > 0 && args[0] == "--probe-type")
        {
            // Probe one xmlns+name resolution via the custom context.
            // Usage: --probe-type <xmlns> <name>
            var ctx = _schemaContext!;
            var xn = args[1];
            var nm = args[2];
            // Try both overloads: GetXamlType(XamlTypeName) AND GetXamlType(xmlns, name).
            var xt1 = ctx.GetXamlType(new XamlTypeName(xn, nm));
            Console.WriteLine($"  via XamlTypeName: {(xt1 == null ? "NULL" : $"{xt1.UnderlyingType?.FullName} in {xt1.UnderlyingType?.Assembly?.GetName().Name}")}");
            // direct (xmlns, name) overload requires "internal" virtual; expose via reflection
            var method = typeof(XamlSchemaContext).GetMethod("GetXamlType", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic, null, new[] { typeof(string), typeof(string), typeof(XamlType[]) }, null);
            if (method != null)
            {
                var xt2 = (XamlType?)method.Invoke(ctx, new object?[] { xn, nm, Array.Empty<XamlType>() });
                Console.WriteLine($"  via (xmlns,name): {(xt2 == null ? "NULL" : $"{xt2.UnderlyingType?.FullName} in {xt2.UnderlyingType?.Assembly?.GetName().Name}")}");
            }
            // Find Type direct via reflection in loaded assemblies
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types;
                try { types = asm.GetTypes(); }
                catch (ReflectionTypeLoadException rtle) { types = rtle.Types.Where(t => t != null).ToArray()!; }
                catch { continue; }
                var found = types.Where(t => t != null && t.Name == nm).Take(2).ToList();
                foreach (var t in found)
                {
                    Console.WriteLine($"  direct CLR match: {t.FullName} in {asm.GetName().Name}");
                }
            }
            // Also probe specific known type via Type.GetType
            var byTypeName = Type.GetType("System.Activities.Activity, System.Activities", throwOnError: false);
            Console.WriteLine($"  Type.GetType: {(byTypeName?.AssemblyQualifiedName ?? "NULL")}");
            return 0;
        }

        if (args.Length > 0 && args[0] == "--dump-types")
        {
            // List every public class in each pre-loaded UiPath.*/CCS_* assembly,
            // grouped by assembly. Output one record per line: "AsmName|FullTypeName".
            // Used to verify which canonical activity types (LogMessage, MessageBox,
            // QueueItem, Click, etc.) actually ship in the public NuGet closure.
            DumpTypes(args.Length > 1 ? args[1] : null);
            return 0;
        }

        var paths = new List<string>();
        if (args.Length > 0 && args[0] == "--stdin")
        {
            string? line;
            while ((line = Console.In.ReadLine()) != null)
            {
                var trimmed = line.Trim();
                if (!string.IsNullOrEmpty(trimmed)) paths.Add(trimmed);
            }
        }
        else if (args.Length > 0)
        {
            paths.AddRange(args);
        }
        else
        {
            Console.Error.WriteLine("Usage: runtime_loadtest [--stdin | <xaml_path>...]");
            return 2;
        }

        var results = new List<LoadResult>();
        foreach (var path in paths)
        {
            results.Add(LoadXaml(path));
        }

        var options = new JsonSerializerOptions { WriteIndented = false };
        Console.WriteLine(JsonSerializer.Serialize(new { results }, options));

        return results.TrueForAll(r => r.Status == "OK") ? 0 : 1;
    }

    /// <summary>
    /// Debug helper: dump XmlnsDefinitionAttribute mappings encontrados
    /// em assemblies pre-loaded. Usado pra investigar gaps de xmlns
    /// resolution (e.g., MessageBox tipo desconhecido).
    /// </summary>
    private static void DumpXmlnsMappings()
    {
        var mapCount = 0;
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            System.Reflection.CustomAttributeData[] customs;
            try { customs = asm.GetCustomAttributesData().ToArray(); }
            catch { continue; }
            foreach (var c in customs)
            {
                var name = c.AttributeType.Name;
                if (name != "XmlnsDefinitionAttribute") continue;
                var ctorArgs = c.ConstructorArguments;
                if (ctorArgs.Count < 2) continue;
                var xmlns = ctorArgs[0].Value?.ToString() ?? "";
                var clr = ctorArgs[1].Value?.ToString() ?? "";
                Console.WriteLine($"{asm.GetName().Name}|{xmlns}|{clr}");
                mapCount++;
            }
        }
        Console.Error.WriteLine($"Total xmlns mappings: {mapCount}");

        // Search MessageBox type
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type[] types;
            try { types = asm.GetTypes(); } catch { continue; }
            foreach (var t in types)
            {
                if (t.Name == "MessageBox")
                {
                    Console.Error.WriteLine($"MessageBox: {t.FullName} in {asm.GetName().Name}");
                }
            }
        }
    }

    /// <summary>
    /// Constrói XamlSchemaContext customizado que enxerga TODOS assemblies
    /// preloaded e injeta fallback resolution para os xmlns que UiPath
    /// public NuGet packages NÃO declaram via XmlnsDefinitionAttribute
    /// (notavelmente "http://schemas.uipath.com/workflow/activities" →
    /// CLR namespaces como UiPath.Core, UiPath.Core.Activities, etc.).
    /// </summary>
    private static XamlSchemaContext BuildSchemaContext()
    {
        // Use ctor SEM references — XamlSchemaContext(settings) default
        // scaneia AppDomain.GetAssemblies() lazily ao primeiro lookup, e
        // refaz scan quando novos assemblies forem carregados. Passar
        // IEnumerable<Assembly> RESTRINGE o scan àquela lista; mesmo
        // passando ALL loaded, a snapshot é tomada na construção e
        // assemblies posteriores não são vistos. Mais robusto: deixar
        // XamlSchemaContext scaneiar AppDomain dinamicamente.
        var settings = new XamlSchemaContextSettings
        {
            SupportMarkupExtensionsWithDuplicateArity = false,
            FullyQualifyAssemblyNamesInClrNamespaces = false,
        };
        return new SicoobXamlSchemaContext(settings);
    }

    /// <summary>
    /// Dump UiPath.* public class types per assembly. Optional filter:
    /// if `filter` is non-null and non-empty, only types whose simple Name
    /// contains the filter (case-insensitive) are emitted.
    /// </summary>
    private static void DumpTypes(string? filter)
    {
        var filterLower = string.IsNullOrEmpty(filter) ? null : filter!.ToLowerInvariant();
        var asmCount = 0;
        var typeCount = 0;
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            var aname = asm.GetName().Name ?? "";
            if (!(aname.StartsWith("UiPath", StringComparison.OrdinalIgnoreCase)
                  || aname.StartsWith("CCS_", StringComparison.OrdinalIgnoreCase)))
            {
                continue;
            }
            asmCount++;
            Type[] types;
            try { types = asm.GetTypes(); }
            catch (System.Reflection.ReflectionTypeLoadException rtle)
            {
                types = rtle.Types.Where(t => t != null).ToArray()!;
            }
            catch { continue; }
            foreach (var t in types)
            {
                if (t == null) continue;
                if (!t.IsPublic) continue;
                if (t.IsInterface) continue;
                if (t.IsAbstract && t.IsSealed) continue; // skip static
                var simple = t.Name ?? "";
                if (filterLower != null && !simple.ToLowerInvariant().Contains(filterLower)) continue;
                Console.WriteLine($"{aname}|{t.FullName}");
                typeCount++;
            }
        }
        Console.Error.WriteLine($"# asms scanned: {asmCount}, types emitted: {typeCount}");
    }

    /// <summary>
    /// Eager-load UiPath/CCS assemblies vizinhos ao exe pra que
    /// XmlnsDefinitionAttribute seja descoberto durante XAML deserialize.
    /// Filtra prefixos seguros (UiPath., CCS_) pra não puxar runtimes
    /// nativos (msvcp140 etc) ou DLLs irrelevantes.
    /// </summary>
    private static void PreloadXmlnsBearingAssemblies()
    {
        var binDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? "";
        var debug = Environment.GetEnvironmentVariable("RT_LOADTEST_DEBUG") == "1";
        var loaded = 0;
        foreach (var dll in Directory.GetFiles(binDir, "*.dll"))
        {
            var name = Path.GetFileNameWithoutExtension(dll);
            // Whitelist: DLLs com xmlns mapping prováveis. UiPath/CCS + core
            // System.Activities.dll (CoreWF runtime types: Activity, Sequence,
            // If, Variable etc. — NÃO carregadas por default mesmo deployadas).
            // Sem o preload de System.Activities, XamlSchemaContext não enxerga
            // o concrete `Activity` type → todos XAMLs falham com
            // "Tipo desconhecido '{http://schemas.microsoft.com/netfx/2009/xaml/activities}Activity'".
            var isUiPath = name.StartsWith("UiPath.", StringComparison.OrdinalIgnoreCase);
            var isCcs = name.StartsWith("CCS_", StringComparison.OrdinalIgnoreCase);
            var isSysActivities = name.Equals("System.Activities", StringComparison.OrdinalIgnoreCase)
                              || name.Equals("System.Activities.Core.Presentation", StringComparison.OrdinalIgnoreCase)
                              || name.Equals("System.ServiceModel.Activities", StringComparison.OrdinalIgnoreCase);
            if (!(isUiPath || isCcs || isSysActivities))
            {
                continue;
            }
            if (name.EndsWith(".resources", StringComparison.OrdinalIgnoreCase)) continue;
            try { Assembly.LoadFrom(dll); loaded++; }
            catch (Exception ex)
            {
                if (debug) Console.Error.WriteLine($"[debug] preload skip {name}: {ex.GetType().Name}");
            }
        }
        if (debug) Console.Error.WriteLine($"[debug] pre-loaded {loaded} UiPath/CCS/SystemActivities assemblies");
    }

    /// <summary>
    /// Carrega XAML via ActivityXamlServices.Load + walka Activity tree
    /// pra force CacheMetadata em cada nested Activity. Captura todas
    /// exception classes documentadas + cai em UNHANDLED pra resto.
    /// </summary>
    public static LoadResult LoadXaml(string path)
    {
        if (!File.Exists(path))
        {
            return new LoadResult { File = path, Status = "NOT_FOUND", Error = "file does not exist" };
        }

        try
        {
            using var stream = File.OpenRead(path);
            var settings = new ActivityXamlServicesSettings
            {
                // CompileExpressions=true força VB expressions em Variable.
                // Default + InArgument/OutArgument bindings a compile EAGERLY.
                // Sem isso, errors em expressions só disparam em runtime
                // execute — defeats purpose do gate.
                CompileExpressions = true,
            };

            // UiPath public NuGet seam doesn't ship XmlnsDefinitionAttribute
            // for the "http://schemas.uipath.com/workflow/activities" URI
            // (Studio injects mappings via its own metadata stores). We use
            // a custom XamlSchemaContext (SicoobXamlSchemaContext) that
            // falls back to scanning known CLR namespaces (UiPath.Core,
            // UiPath.Core.Activities, etc.) when base resolution returns null.
            var readerSettings = new XamlXmlReaderSettings();
            using var xmlReader = System.Xml.XmlReader.Create(stream);
            using var reader = new XamlXmlReader(xmlReader, _schemaContext, readerSettings);
            var activity = ActivityXamlServices.Load(reader, settings);
            if (activity == null)
            {
                return new LoadResult { File = path, Status = "LOAD_NULL", Error = "ActivityXamlServices.Load returned null" };
            }

            // CacheMetadata força bindings + type resolution em cada nested
            // Activity. Throws InvalidWorkflowException ou ValidationException
            // se metadata inválida (e.g., required arg sem binding, type
            // unresolved, etc).
            foreach (var child in WorkflowInspectionServices.GetActivities(activity))
            {
                WorkflowInspectionServices.CacheMetadata(child);
            }
            // CacheMetadata em root também pra captar metadata-level errors.
            WorkflowInspectionServices.CacheMetadata(activity);

            return new LoadResult { File = path, Status = "OK" };
        }
        catch (InvalidWorkflowException iwe)
        {
            return new LoadResult
            {
                File = path,
                Status = "INVALID_WORKFLOW",
                Category = "metadata",
                Error = iwe.Message,
            };
        }
        catch (XamlObjectWriterException xowe)
        {
            return new LoadResult
            {
                File = path,
                Status = "XAML_OBJECT_WRITER",
                Category = "deserialize",
                Error = xowe.Message,
                Line = xowe.LineNumber > 0 ? xowe.LineNumber : null,
            };
        }
        catch (XamlParseException xpe)
        {
            return new LoadResult
            {
                File = path,
                Status = "XAML_PARSE",
                Category = "deserialize",
                Error = xpe.Message,
                Line = xpe.LineNumber > 0 ? xpe.LineNumber : null,
            };
        }
        catch (ValidationException ve)
        {
            return new LoadResult
            {
                File = path,
                Status = "VALIDATION",
                Category = "validation",
                Error = ve.Message,
            };
        }
        catch (Exception ex)
        {
            return new LoadResult
            {
                File = path,
                Status = "UNHANDLED",
                Category = "unknown",
                Error = $"{ex.GetType().FullName}: {ex.Message}",
            };
        }
    }
}

/// <summary>
/// Custom XamlSchemaContext que injeta fallback xmlns → CLR namespace
/// mappings que UiPath public NuGet packages NÃO declaram.
///
/// Quando base resolution via XmlnsDefinitionAttribute scan retorna null,
/// tenta resolver via lista hardcoded de CLR namespaces que sabidamente
/// contêm tipos sob aquele xmlns URI. Por exemplo:
///
///   "http://schemas.uipath.com/workflow/activities" →
///       UiPath.Core, UiPath.Core.Activities,
///       UiPath.Core.Activities.Storage, UiPath.Core.Activities.Orchestrator,
///       UiPath.Core.Activities.DateModifications,
///       UiPath.Core.Activities.TextModifications, ...
///
/// Mapping descoberto via inspeção de UiPath.System.Activities.dll e
/// UiPath.UiAutomation.Activities.dll do feed UiPath-Official 25.4.4 /
/// 25.10.8 (vide .tmp/phase_1a1_all_types.txt).
/// </summary>
internal class SicoobXamlSchemaContext : XamlSchemaContext
{
    private readonly List<Assembly> _refs;
    private readonly ConcurrentDictionary<string, XamlType?> _cache = new();

    /// <summary>Ctor sem references: usa default scan (all loaded assemblies).
    /// Reflexão é amortizada pela cache interna de XamlSchemaContext.</summary>
    public SicoobXamlSchemaContext(XamlSchemaContextSettings settings)
        : base(settings)
    {
        _refs = AppDomain.CurrentDomain.GetAssemblies()
            .Where(a => !a.IsDynamic)
            .ToList();
    }

    // Fallback CLR namespaces per xmlns URI. Order matters somewhat (mais
    // específico primeiro pra hits mais comuns). Tipos do XAML são resolvidos
    // tentando cada CLR ns + assembly até encontrar.
    private static readonly Dictionary<string, string[]> XmlnsClrNamespaces = new()
    {
        ["http://schemas.uipath.com/workflow/activities"] = new[]
        {
            "UiPath.Core.Activities",
            "UiPath.Core",
            "UiPath.Core.Activities.Storage",
            "UiPath.Core.Activities.Orchestrator",
            "UiPath.Core.Activities.DateModifications",
            "UiPath.Core.Activities.TextModifications",
            "UiPath.Core.Activities.ProcessTracking",
            "UiPath.Core.Activities.TimeTriggerUtilities",
            "UiPath.Core.Activities.SAP",
            "UiPath.Core.Activities.ScopeActivities",
            "UiPath.Core.Activities.UiTree",
            "UiPath.Core.Activities.Anchor2",
            "UiPath.Core.Activities.SyncObjects",
            "UiPath.Core.Activities.Properties",
            "UiPath.Core.Format",
            "UiPath.Shared.Activities",
            "UiPath.Activities.System.Jobs",
            "UiPath.Activities.System.Collections.Filters",
        },
        ["http://schemas.uipath.com/workflow/activities/uix"] = new[]
        {
            "UiPath.UIAutomationNext.Activities",
            "UiPath.UIAutomationNext.Activities.Triggers",
            "UiPath.UIAutomationNext.API.Models",
            "UiPath.UIAutomationNext.Enums",
            "UiPath.UIAutomationNext.Exceptions",
            "UiPath.UIAutomationNext",
        },
        // Core System.Activities xmlns: UiPath.Workflow DECLARES o
        // XmlnsDefinitionAttribute apontando p/ namespaces System.Activities*,
        // mas o tipo concreto (e.g. Activity, Sequence) vive no assembly
        // SEPARADO `System.Activities`. XamlSchemaContext base não cruza
        // a fronteira de assembly. Fallback aqui mira diretamente os
        // CLR namespaces certos.
        ["http://schemas.microsoft.com/netfx/2009/xaml/activities"] = new[]
        {
            "System.Activities",
            "System.Activities.Statements",
            "System.Activities.Expressions",
            "System.Activities.Validation",
            "System.Activities.XamlIntegration",
            "Microsoft.VisualBasic.Activities",
            "Microsoft.CSharp.Activities",
        },
        ["http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger"] = new[]
        {
            "System.Activities.Debugger.Symbol",
        },
    };

    public SicoobXamlSchemaContext(IEnumerable<Assembly> references, XamlSchemaContextSettings settings)
        : base(references, settings)
    {
        _refs = references.ToList();
    }

    protected override XamlType GetXamlType(string xmlNamespace, string name, params XamlType[] typeArguments)
    {
        var debug = Environment.GetEnvironmentVariable("RT_LOADTEST_DEBUG") == "1";
        // Try base first (covers xmlns w/ XmlnsDefinitionAttribute + clr-namespace:).
        var t = base.GetXamlType(xmlNamespace, name, typeArguments);
        if (debug) Console.Error.WriteLine($"[ctx] GetXamlType base xmlns={xmlNamespace} name={name} -> {t?.UnderlyingType?.FullName ?? "NULL"}");
        if (t != null && t.UnderlyingType != null) return t;

        // Cache key includes generic arity to avoid collisions.
        var arity = typeArguments?.Length ?? 0;
        var key = $"{xmlNamespace}|{name}|{arity}";
        var cached = _cache.GetOrAdd(key, _ => TryResolveFallback(xmlNamespace, name, typeArguments));
        if (debug) Console.Error.WriteLine($"[ctx] fallback xmlns={xmlNamespace} name={name} -> {cached?.UnderlyingType?.FullName ?? "NULL"}");
        return cached ?? t!;  // t may be null too; xaml engine will then report unknown type
    }

    private XamlType? TryResolveFallback(string xmlNamespace, string name, XamlType[] typeArguments)
    {
        var debug = Environment.GetEnvironmentVariable("RT_LOADTEST_DEBUG") == "1";
        if (!XmlnsClrNamespaces.TryGetValue(xmlNamespace, out var clrNamespaces))
        {
            if (debug) Console.Error.WriteLine($"[fallback] no fallback mapping for xmlns={xmlNamespace}");
            return null;
        }

        // Generic name: "ForEach`1" sometimes given as just "ForEach" with typeArguments.
        // Build candidate type name including arity if needed.
        var arity = typeArguments?.Length ?? 0;
        var lookupName = arity > 0 ? $"{name}`{arity}" : name;

        // Re-snapshot AppDomain each call — assemblies may have been loaded
        // between ctor and lookup. Cheap (cache hits dominate).
        var asms = AppDomain.CurrentDomain.GetAssemblies()
            .Where(a => !a.IsDynamic)
            .ToList();

        foreach (var clrNs in clrNamespaces)
        {
            var candidate = $"{clrNs}.{lookupName}";
            foreach (var asm in asms)
            {
                Type? resolved;
                try { resolved = asm.GetType(candidate, throwOnError: false); }
                catch { continue; }
                if (resolved == null) continue;

                if (debug) Console.Error.WriteLine($"[fallback] hit: {resolved.FullName} in {asm.GetName().Name}");

                if (arity > 0 && typeArguments != null)
                {
                    var typeArgClr = typeArguments.Where(ta => ta?.UnderlyingType != null)
                                                  .Select(ta => ta.UnderlyingType!).ToArray();
                    if (typeArgClr.Length == arity)
                    {
                        try { resolved = resolved.MakeGenericType(typeArgClr); }
                        catch { /* fall through with open generic */ }
                    }
                }
                return GetXamlType(resolved);
            }
        }
        if (debug) Console.Error.WriteLine($"[fallback] miss: xmlns={xmlNamespace} name={name} tried {clrNamespaces.Length} clr ns x {asms.Count} asms");
        return null;
    }
}

/// <summary>
/// Resultado per-XAML. Serializado direto pra JSON (PascalCase).
/// Wrapper Python lê tanto PascalCase quanto camelCase.
/// </summary>
public class LoadResult
{
    public string File { get; set; } = "";
    public string Status { get; set; } = "";
    public string? Error { get; set; }
    public string? Category { get; set; }
    public int? Line { get; set; }
}
