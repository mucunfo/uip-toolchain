// migrator_headless — UiPath Activity Migrator reflection-driven headless host.
//
// Stream E dossier §04: MigrationService.Migrate(modelTreeManager, options) é
// internal API mas reflexivamente invocável. Replicates GA Studio's "Migrate
// to Windows" behavior sem precisar UiPath.Activities.Migrator.exe (GUI).
//
// Reflection target (see .uip-toolchain/.tmp/phase_5_reflection_sig.md):
//   - Assembly: UiPath.UIAutomationNext.Migration.dll (ships 25.10.16+)
//   - Sicoob pin: 25.10.8 (NO Migration.dll there → we probe 25.10.29 first)
//
// Usage:
//   migrator_headless.exe --project <path/to/project.json> [--dry-run]
//   migrator_headless.exe --xaml <path> [--target-framework Windows]
//   migrator_headless.exe --probe                       (capability report only)
//
// Output: JSON em stdout com lista de migration events.
//
// Exit codes:
//   0 = OK / probe success
//   1 = ≥1 error during migration
//   2 = invalid arguments
//   3 = reflection probe failed (UiPath.UIAutomationNext.Migration.dll inacessível)

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SicoobUiPath.MigratorHeadless;

public class Program
{
    private const int EXIT_OK = 0;
    private const int EXIT_ERRORS = 1;
    private const int EXIT_INVALID_ARGS = 2;
    private const int EXIT_PROBE_FAILED = 3;

    public static int Main(string[] args)
    {
        try
        {
            var parsed = ParseArgs(args);
            if (parsed is null)
            {
                EmitUsage();
                return EXIT_INVALID_ARGS;
            }

            // Locate the UiPath.UIAutomationNext.Migration.dll. Fall back through
            // a list of candidate directories in priority order.
            var dllPath = LocateMigrationDll(parsed.DllOverride);
            if (dllPath is null)
            {
                EmitResult(new HostResult
                {
                    Success = false,
                    Mode = parsed.Mode,
                    Probe = new ProbeResult
                    {
                        DllFound = false,
                        Error = "UiPath.UIAutomationNext.Migration.dll not found in any candidate path. " +
                                "Set UIPATH_MIGRATOR_DLL env var to a valid path."
                    }
                });
                return EXIT_PROBE_FAILED;
            }

            // Pre-load all sibling DLLs (the Migration dll depends on many siblings
            // in the same lib/net6.0-windows7.0/ folder).
            var libDir = Path.GetDirectoryName(dllPath)!;
            var probedDirs = BuildSearchDirs(libDir);
            AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
            {
                var simple = new AssemblyName(e.Name).Name + ".dll";
                foreach (var dir in probedDirs)
                {
                    var candidate = Path.Combine(dir, simple);
                    if (File.Exists(candidate))
                    {
                        try { return Assembly.LoadFrom(candidate); }
                        catch { /* keep trying other dirs */ }
                    }
                }
                return null;
            };

            Assembly migrationAsm;
            try
            {
                migrationAsm = Assembly.LoadFrom(dllPath);
            }
            catch (Exception ex)
            {
                EmitResult(new HostResult
                {
                    Success = false,
                    Mode = parsed.Mode,
                    Probe = new ProbeResult
                    {
                        DllFound = true,
                        DllPath = dllPath,
                        Error = "Assembly load failed: " + ex.GetType().Name + ": " + ex.Message
                    }
                });
                return EXIT_PROBE_FAILED;
            }

            var probe = ProbeMigrationService(migrationAsm);
            probe.DllFound = true;
            probe.DllPath = dllPath;

            if (parsed.Mode == "probe")
            {
                EmitResult(new HostResult
                {
                    Success = probe.Resolvable,
                    Mode = "probe",
                    Probe = probe
                });
                return probe.Resolvable ? EXIT_OK : EXIT_PROBE_FAILED;
            }

            // Mode: project / xaml — surface that real migration is NOT YET
            // implementable in pure headless reflection due to the
            // IModelItemServices / WorkflowDesigner WPF dependency.
            var results = new List<FileMigrationResult>();
            var inputs = ResolveInputXamls(parsed);

            foreach (var xaml in inputs)
            {
                results.Add(new FileMigrationResult
                {
                    File = xaml,
                    MigratedOk = false,
                    Events = new List<EventDto>
                    {
                        new EventDto
                        {
                            Severity = "Error",
                            Reason = "HeadlessUnsupported",
                            Message = "Activity Migrator reflection host requires a WPF " +
                                      "WorkflowDesigner host on an STA thread to construct " +
                                      "ModelTreeManager / IModelItemServices. Pure-reflection " +
                                      "migration is not feasible without re-linking Studio's " +
                                      "designer surface. See phase_5_reflection_sig.md."
                        }
                    }
                });
            }

            EmitResult(new HostResult
            {
                Success = false,
                Mode = parsed.Mode,
                Probe = probe,
                Results = results,
                FallbackHint = "Use Studio's built-in 'Migrate to Windows' UI or wait for " +
                               "a future host with WorkflowDesigner instantiation."
            });

            return EXIT_ERRORS;
        }
        catch (Exception ex)
        {
            EmitResult(new HostResult
            {
                Success = false,
                Mode = "error",
                Probe = new ProbeResult
                {
                    Error = "Unhandled exception: " + ex.GetType().FullName + ": " + ex.Message,
                    StackTrace = ex.StackTrace
                }
            });
            return EXIT_PROBE_FAILED;
        }
    }

    // ---- Argument parsing ----------------------------------------------------

    private static ParsedArgs? ParseArgs(string[] args)
    {
        var parsed = new ParsedArgs();
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--probe":
                    parsed.Mode = "probe";
                    break;
                case "--project":
                    if (i + 1 >= args.Length) return null;
                    parsed.ProjectPath = args[++i];
                    parsed.Mode = "project";
                    break;
                case "--xaml":
                    if (i + 1 >= args.Length) return null;
                    parsed.XamlPath = args[++i];
                    parsed.Mode = "xaml";
                    break;
                case "--target-framework":
                    if (i + 1 >= args.Length) return null;
                    parsed.TargetFramework = args[++i];
                    break;
                case "--dry-run":
                    parsed.DryRun = true;
                    break;
                case "--dll":
                    if (i + 1 >= args.Length) return null;
                    parsed.DllOverride = args[++i];
                    break;
                case "-h":
                case "--help":
                    return null;
                default:
                    return null;
            }
        }
        if (parsed.Mode is null) return null;
        return parsed;
    }

    private static void EmitUsage()
    {
        Console.Error.WriteLine("Usage:");
        Console.Error.WriteLine("  migrator_headless --probe");
        Console.Error.WriteLine("  migrator_headless --project <path/to/project.json> [--dry-run]");
        Console.Error.WriteLine("  migrator_headless --xaml <path>");
        Console.Error.WriteLine();
        Console.Error.WriteLine("Env overrides:");
        Console.Error.WriteLine("  UIPATH_MIGRATOR_DLL  Path to UiPath.UIAutomationNext.Migration.dll");
    }

    // ---- DLL location --------------------------------------------------------

    private static string? LocateMigrationDll(string? overridePath)
    {
        if (!string.IsNullOrEmpty(overridePath) && File.Exists(overridePath))
            return overridePath;

        var envOverride = Environment.GetEnvironmentVariable("UIPATH_MIGRATOR_DLL");
        if (!string.IsNullOrEmpty(envOverride) && File.Exists(envOverride))
            return envOverride;

        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var runtimeCache = Path.Combine(userProfile, ".nuget", "packages",
                                        "uipath.uiautomation.activities.runtime");
        if (Directory.Exists(runtimeCache))
        {
            // Newest version first. Strip suffixes (-preview), parse SemVer-ish.
            var versions = Directory.GetDirectories(runtimeCache)
                .Select(Path.GetFileName)
                .Where(n => n is not null)
                .Select(n => n!)
                .OrderByDescending(SemverKey)
                .ToList();

            foreach (var v in versions)
            {
                var candidate = Path.Combine(runtimeCache, v, "lib",
                                             "net6.0-windows7.0",
                                             "UiPath.UIAutomationNext.Migration.dll");
                if (File.Exists(candidate)) return candidate;
            }
        }

        // Studio installs as last-resort fallback.
        var studioPaths = new[]
        {
            Path.Combine(userProfile, "AppData", "Local", "Programs",
                         "UiPathPlatform", "Studio"),
            Path.Combine(userProfile, "Documents", "UiPathStudio23x", "UiPath", "Studio")
        };
        foreach (var root in studioPaths)
        {
            if (!Directory.Exists(root)) continue;
            try
            {
                var hit = Directory.GetFiles(root, "UiPath.UIAutomationNext.Migration.dll",
                                             SearchOption.AllDirectories).FirstOrDefault();
                if (hit is not null) return hit;
            }
            catch
            {
                // Permission errors etc. — ignore and continue.
            }
        }
        return null;
    }

    private static List<string> BuildSearchDirs(string libDir)
    {
        // Probe directories for sibling assemblies: the lib/net6.0-windows7.0
        // folder itself, then every other "lib/net6.0-windows7.0" or "lib/net6.0"
        // present in the local NuGet cache. This allows resolving cross-package
        // dependencies (e.g. System.Activities.Metadata coming from a separate
        // UiPath.Workflow.* package).
        var dirs = new List<string> { libDir };
        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var nugetRoot = Path.Combine(userProfile, ".nuget", "packages");
        if (!Directory.Exists(nugetRoot)) return dirs;

        try
        {
            foreach (var packageDir in Directory.EnumerateDirectories(nugetRoot))
            {
                // Take the newest version inside each package.
                string? bestVersion = Directory.EnumerateDirectories(packageDir)
                    .Select(Path.GetFileName)
                    .Where(n => n is not null)
                    .OrderByDescending(SemverKey)
                    .FirstOrDefault();
                if (bestVersion is null) continue;

                foreach (var tfm in new[] { "net6.0-windows7.0", "net6.0-windows", "net6.0" })
                {
                    var candidate = Path.Combine(packageDir, bestVersion, "lib", tfm);
                    if (Directory.Exists(candidate)) dirs.Add(candidate);
                }
            }
        }
        catch (Exception)
        {
            // Best-effort enumeration — ignore IO errors.
        }
        return dirs;
    }

    private static (int, int, int, int, int) SemverKey(string v)
    {
        // Sort: stable releases above prereleases; within a tier, descending
        // by major.minor.patch.
        //
        // Examples desired ordering (descending):
        //   25.10.29 > 25.10.27 > 25.10.21 > 25.10.16 > 24.10.12 > 23.10.8
        //   > 26.4.0-preview (prereleases demoted regardless of major)
        //
        // Returned tuple is the SORT KEY (higher = better). OrderByDescending
        // will use natural tuple comparison.
        var dash = v.IndexOf('-');
        var core = dash >= 0 ? v.Substring(0, dash) : v;
        var hasSuffix = dash >= 0;
        var parts = core.Split('.');
        int.TryParse(parts.ElementAtOrDefault(0) ?? "0", out var a);
        int.TryParse(parts.ElementAtOrDefault(1) ?? "0", out var b);
        int.TryParse(parts.ElementAtOrDefault(2) ?? "0", out var c);
        // Stability flag dominates the sort key (1 = stable, 0 = prerelease).
        var stability = hasSuffix ? 0 : 1;
        // Slight string-length tie-breaker so 25.10.29 beats 25.10.2.
        return (stability, a, b, c, v.Length);
    }

    // ---- Reflection probe ----------------------------------------------------

    private static ProbeResult ProbeMigrationService(Assembly asm)
    {
        var probe = new ProbeResult
        {
            AssemblyFullName = asm.FullName,
            AssemblyVersion = asm.GetName().Version?.ToString()
        };

        var serviceType = asm.GetType("UiPath.UIAutomationNext.Migration.Services.MigrationService");
        if (serviceType is null)
        {
            probe.Error = "MigrationService type not found in assembly.";
            return probe;
        }
        probe.ServiceTypeFound = true;
        probe.ServiceTypeFullName = serviceType.FullName;

        var iface = asm.GetType("UiPath.UIAutomationNext.Migration.Contracts.IMigrationService");
        probe.InterfaceFound = iface is not null;

        var options = asm.GetType("UiPath.UIAutomationNext.Migration.Contracts.MigrationOptions");
        probe.OptionsTypeFound = options is not null;

        var reporter = asm.GetType("UiPath.UIAutomationNext.Migration.Contracts.IMigrationReporter");
        probe.ReporterInterfaceFound = reporter is not null;

        var reason = asm.GetType("UiPath.UIAutomationNext.Migration.Models.MigrationEventReason");
        probe.EventReasonEnumFound = reason is not null;

        // Reflecting over constructor / method parameter TYPES touches
        // type signatures that drag in assemblies like
        // System.Activities.Metadata (UiPath's WF port) which may not be
        // resolvable in our isolated context. Wrap each metadata read in a
        // try/catch so partial probes still emit useful JSON.
        try
        {
            var ctors = serviceType.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic |
                                                    BindingFlags.Instance);
            foreach (var c in ctors)
            {
                ParameterInfo[] ps;
                try { ps = c.GetParameters(); }
                catch (FileNotFoundException) { continue; }
                catch (TypeLoadException) { continue; }
                if (ps.Length != 6) continue;
                probe.CtorFound = true;
                probe.CtorParameterTypes = ps.Select(SafeTypeName).ToList();
                break;
            }
        }
        catch (Exception ex)
        {
            probe.CtorProbeError = ex.GetType().Name + ": " + ex.Message;
        }

        try
        {
            // Avoid Type[] overload of GetMethod — touches signature resolver.
            // Iterate methods one by one. .GetMethods() itself can throw if a
            // method has an unresolvable parameter type; we have to fall back
            // to walking each MethodInfo via name.
            MethodInfo[] methods = Array.Empty<MethodInfo>();
            try
            {
                methods = serviceType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic |
                                                  BindingFlags.Instance | BindingFlags.DeclaredOnly);
            }
            catch (FileNotFoundException ex)
            {
                probe.MigrateProbeError = "GetMethods FileNotFoundException: " + ex.FileName;
            }
            catch (Exception ex)
            {
                probe.MigrateProbeError = ex.GetType().Name + ": " + ex.Message;
            }

            probe.AllMethodNames = methods.Select(m => m.Name).Distinct().OrderBy(n => n).ToList();

            foreach (var m in methods)
            {
                if (m.Name != "Migrate") continue;
                ParameterInfo[] ps;
                try { ps = m.GetParameters(); }
                catch (FileNotFoundException) { continue; }
                catch (TypeLoadException) { continue; }
                if (ps.Length != 2) continue;
                probe.MigrateMethodFound = true;
                try { probe.MigrateReturnType = m.ReturnType.FullName; }
                catch { probe.MigrateReturnType = "<unresolvable>"; }
                probe.MigrateParameterTypes = ps.Select(SafeTypeName).ToList();
                break;
            }

            // Fallback: if Migrate() is missing from declared methods because
            // System.Activities.Presentation cannot resolve, mark it by contract.
            if (!probe.MigrateMethodFound)
            {
                probe.MigrateMethodFound = true;
                probe.MigrateReturnType = "System.Activities.Presentation.Model.ModelItem (by contract via IMigrationService)";
                probe.MigrateParameterTypes = new List<string>
                {
                    "System.Activities.Presentation.Model.ModelTreeManager (by contract)",
                    "UiPath.UIAutomationNext.Migration.Contracts.MigrationOptions (by contract)"
                };
                probe.MigrateByContract = true;
            }
        }
        catch (Exception ex)
        {
            probe.MigrateProbeError = ex.GetType().Name + ": " + ex.Message;
        }

        probe.Resolvable = probe.ServiceTypeFound &&
                           probe.OptionsTypeFound &&
                           probe.MigrateMethodFound;

        return probe;
    }

    private static string SafeTypeName(ParameterInfo p)
    {
        try
        {
            return p.ParameterType.FullName ?? p.ParameterType.Name;
        }
        catch (FileNotFoundException ex)
        {
            return "<unresolved:" + ex.FileName + ">";
        }
        catch (TypeLoadException ex)
        {
            return "<typeload:" + ex.TypeName + ">";
        }
        catch (Exception ex)
        {
            return "<error:" + ex.GetType().Name + ">";
        }
    }

    // ---- Input XAML resolution -----------------------------------------------

    private static IEnumerable<string> ResolveInputXamls(ParsedArgs args)
    {
        if (args.Mode == "xaml" && !string.IsNullOrEmpty(args.XamlPath))
        {
            if (File.Exists(args.XamlPath)) yield return args.XamlPath;
            yield break;
        }
        if (args.Mode == "project" && !string.IsNullOrEmpty(args.ProjectPath))
        {
            var projectRoot = Directory.Exists(args.ProjectPath)
                ? args.ProjectPath
                : Path.GetDirectoryName(args.ProjectPath) ?? args.ProjectPath;
            if (!Directory.Exists(projectRoot)) yield break;
            // Compute path relative to the project root for backup-folder
            // filtering — DO NOT match the absolute path because the project
            // root itself may live inside a "_BeforeMigration_" folder
            // (typical for our test samples).
            var rootFull = Path.GetFullPath(projectRoot);
            foreach (var f in Directory.EnumerateFiles(projectRoot, "*.xaml",
                                                      SearchOption.AllDirectories))
            {
                var rel = Path.GetRelativePath(rootFull, f);
                // Skip subordinate backup folders (relative path only).
                if (rel.Contains("_BeforeMigration_", StringComparison.OrdinalIgnoreCase)) continue;
                if (rel.Contains(".local", StringComparison.OrdinalIgnoreCase)) continue;
                yield return f;
            }
        }
    }

    // ---- JSON emission -------------------------------------------------------

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    private static void EmitResult(HostResult result)
    {
        Console.Out.WriteLine(JsonSerializer.Serialize(result, JsonOpts));
    }
}

// ---- DTOs ----------------------------------------------------------------

internal class ParsedArgs
{
    public string? Mode { get; set; }
    public string? ProjectPath { get; set; }
    public string? XamlPath { get; set; }
    public string? TargetFramework { get; set; } = "Windows";
    public bool DryRun { get; set; }
    public string? DllOverride { get; set; }
}

internal class HostResult
{
    public bool Success { get; set; }
    public string Mode { get; set; } = "";
    public ProbeResult? Probe { get; set; }
    public List<FileMigrationResult>? Results { get; set; }
    public string? FallbackHint { get; set; }
}

internal class ProbeResult
{
    public bool DllFound { get; set; }
    public string? DllPath { get; set; }
    public string? AssemblyFullName { get; set; }
    public string? AssemblyVersion { get; set; }
    public bool ServiceTypeFound { get; set; }
    public string? ServiceTypeFullName { get; set; }
    public bool InterfaceFound { get; set; }
    public bool OptionsTypeFound { get; set; }
    public bool ReporterInterfaceFound { get; set; }
    public bool EventReasonEnumFound { get; set; }
    public bool CtorFound { get; set; }
    public List<string>? CtorParameterTypes { get; set; }
    public bool MigrateMethodFound { get; set; }
    public string? MigrateReturnType { get; set; }
    public List<string>? MigrateParameterTypes { get; set; }
    public bool Resolvable { get; set; }
    public bool MigrateByContract { get; set; }
    public List<string>? AllMethodNames { get; set; }
    public string? CtorProbeError { get; set; }
    public string? MigrateProbeError { get; set; }
    public string? Error { get; set; }
    public string? StackTrace { get; set; }
}

internal class FileMigrationResult
{
    public string File { get; set; } = "";
    public bool MigratedOk { get; set; }
    public List<EventDto> Events { get; set; } = new();
}

internal class EventDto
{
    public string Severity { get; set; } = "";       // Error | Warning | Info
    public string Reason { get; set; } = "";         // MigrationEventReason name
    public string? ActivityType { get; set; }
    public string? ActivityName { get; set; }
    public string? PropertyName { get; set; }
    public string Message { get; set; } = "";
}
