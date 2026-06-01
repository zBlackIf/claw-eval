using PipelineEngine.Core.Pipeline;
using PipelineEngine.Executors;

namespace PipelineEngine.Registration;

/// <summary>
/// Module that registers all node executors. Add new executor registrations here.
/// </summary>
public static class SystemModule
{
    public static NodeExecutorRegistry CreateRegistry()
    {
        var registry = new NodeExecutorRegistry();
        registry.Register(new StepExecutor());
        registry.Register(new GroupExecutor(registry));
        // TODO: Register new node executors here as they are implemented
        return registry;
    }
}
