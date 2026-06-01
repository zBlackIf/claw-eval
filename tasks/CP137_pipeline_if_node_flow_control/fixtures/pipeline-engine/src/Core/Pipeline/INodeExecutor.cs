namespace PipelineEngine.Core.Pipeline;

/// <summary>
/// Interface for node executors. Each node type has its own executor.
/// </summary>
public interface INodeExecutor<in TNode> where TNode : PipelineNode
{
    Task ExecuteAsync(TNode node, PipelineContext context, CancellationToken ct = default);
}
