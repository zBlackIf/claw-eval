# Rust Notes (existing)

## tokio basics
- Project uses tokio 1.x + axum framework
- Know basic #[tokio::main] macro usage
- spawn creates new tasks

## Topics to study
- Future trait internals
- Why Pin exists
- Arc<Mutex<T>> vs tokio::sync::Mutex
- reqwest Client connection pool reuse
- Use spawn_blocking for blocking ops

## Interview questions I was asked
- How many tokio runtime types? What is the difference? (answered poorly)
- What is Pin? Why is it needed? (could not answer)
