namespace PipelineEngine.Core.Pipeline;

/// <summary>
/// Runtime context for pipeline execution. Holds variables and execution state.
/// </summary>
public class PipelineContext
{
    private readonly Dictionary<string, object?> _variables = new();

    public void SetVariable(string name, object? value)
    {
        _variables[name] = value;
    }

    public object? GetVariable(string name)
    {
        return _variables.TryGetValue(name, out var value) ? value : null;
    }

    public bool HasVariable(string name) => _variables.ContainsKey(name);

    public IReadOnlyDictionary<string, object?> Variables => _variables;

    public bool IsCancelled { get; set; }
}
