using PipelineEngine.Core.Pipeline;

namespace PipelineEngine.Executors;

/// <summary>
/// Registry that maps node types to their executors and dispatches execution.
/// </summary>
public class NodeExecutorRegistry
{
    private readonly Dictionary<Type, object> _executors = new();

    public void Register<TNode>(INodeExecutor<TNode> executor) where TNode : PipelineNode
    {
        _executors[typeof(TNode)] = executor;
    }

    public async Task ExecuteNodeAsync(PipelineNode node, PipelineContext context, CancellationToken ct = default)
    {
        var nodeType = node.GetType();
        if (!_executors.TryGetValue(nodeType, out var executor))
        {
            throw new InvalidOperationException($"No executor registered for node type: {nodeType.Name}");
        }

        // Use reflection to call the typed ExecuteAsync
        var method = executor.GetType().GetMethod("ExecuteAsync");
        if (method == null)
            throw new InvalidOperationException($"Executor for {nodeType.Name} does not have ExecuteAsync method");

        var task = (Task)method.Invoke(executor, new object[] { node, context, ct })!;
        await task;
    }

    public bool HasExecutor<TNode>() where TNode : PipelineNode
    {
        return _executors.ContainsKey(typeof(TNode));
    }
}
