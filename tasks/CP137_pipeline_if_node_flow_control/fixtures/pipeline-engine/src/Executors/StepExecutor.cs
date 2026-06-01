using PipelineEngine.Core.Pipeline;

namespace PipelineEngine.Executors;

/// <summary>
/// Executor for StepPipelineNode. Simulates running an action step.
/// </summary>
public class StepExecutor : INodeExecutor<StepPipelineNode>
{
    public Task ExecuteAsync(StepPipelineNode node, PipelineContext context, CancellationToken ct = default)
    {
        // In production this would dispatch the action to the appropriate handler.
        // For now, just mark execution in context.
        context.SetVariable($"__step_{node.Id}_executed", true);
        return Task.CompletedTask;
    }
}
