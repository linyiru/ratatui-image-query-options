# ratatui-image: what `QueryStdioOptions` changes

A minimal measurement of two options of
[ratatui-image](https://github.com/ratatui/ratatui-image) 12.0.0-rc.0's
`Picker::from_query_stdio_with_options`, against `Picker::from_query_stdio()`:

- `timeout_ms`: how long the query waits for a terminal that never answers.
- `kitty_shared_memory_object`: probe kitty's shared memory transmission
  (`t=s`), and use it where the terminal reads it back.

The function's documentation says it "should ONLY be used if
`Capability::TextSizingProtocol` is needed", which reads as if these
options were not meant for general use.

## Results (verified 2026-10-02)

Arch Linux (kernel 7.2.5), Ryzen 7 8745HS, Hyprland, Ghostty 1.3.1. Medians
of 10 runs, each mode alternated with the other. Raw output:
[results/2026-10-02-starship-ghostty-1.3.1.txt](results/2026-10-02-starship-ghostty-1.3.1.txt).

A pseudo-terminal that answers nothing:

| | `from_query_stdio()` | `timeout_ms: 500` |
|---|---|---|
| query | 2005 ms | 504 ms |

Ghostty 1.3.1, one 640×640 picture fitted to 32×16 cells (448×448 px):

| | `from_query_stdio()` | `kitty_shared_memory_object` |
|---|---|---|
| capabilities | `Kitty, CellSize` | `Kitty, KittySharedMemory, CellSize` |
| `new_protocol` | 14.6 ms | 10.1 ms |
| the frame that sends it | 63.4 ms | 0.21 ms |
| objects left in `/dev/shm` | | 0 |

The machine was busy with other work (load 9.7 to 19.7) during the recorded
run. An earlier run at load 10.9 gave the same picture: frame 23.0 ms
against 0.10 ms, `new_protocol` 5.7 ms against 5.0 ms.

## Run it

```sh
cargo build --release
./run.py silent
./run.py terminal --launch 'ghostty -e {cmd}'
```

`terminal` opens one terminal window per run. Results are written to a file,
since the terminal is what is being measured.
