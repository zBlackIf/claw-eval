using System.Text.Json.Serialization;

namespace PipelineEngine.Core.Pipeline;

/// <summary>
/// Base class for all pipeline nodes. Uses polymorphic deserialization.
/// </summary>
[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]
[JsonDerivedType(typeof(StepPipelineNode), "step")]
[JsonDerivedType(typeof(GroupPipelineNode), "group")]
public abstract record PipelineNode
{
    public required string Id { get; init; }
    public string? Label { get; init; }
}

public record StepPipelineNode : PipelineNode
{
    public required string Action { get; init; }
    public Dictionary<string, object>? Parameters { get; init; }
}

public record GroupPipelineNode : PipelineNode
{
    public List<PipelineNode> Children { get; init; } = new();
}
