using PipelineEngine.Core.Pipeline;

namespace PipelineEngine.Executors;

/// <summary>
/// Executor for GroupPipelineNode. Runs children sequentially.
/// </summary>
public class GroupExecutor : INodeExecutor<GroupPipelineNode>
{
    private readonly NodeExecutorRegistry _registry;

    public GroupExecutor(NodeExecutorRegistry registry)
    {
        _registry = registry;
    }

    public async Task ExecuteAsync(GroupPipelineNode node, PipelineContext context, CancellationToken ct = default)
    {
        foreach (var child in node.Children)
        {
            if (context.IsCancelled) break;
            await _registry.ExecuteNodeAsync(child, context, ct);
        }
    }
}
