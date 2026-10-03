//! Times ratatui-image's terminal query, and the first frame with a kitty
//! image, with and without `QueryStdioOptions`.
//!
//!     query-options <default|timeout=MS|shm> <OUT>
//!
//! The terminal is what is being measured, so the results go to OUT, one
//! `key=value` line per run.

use std::fs::OpenOptions;
use std::io::Write;
use std::time::Instant;

use image::{DynamicImage, RgbImage};
use ratatui::layout::Rect;
use ratatui_image::picker::cap_parser::QueryStdioOptions;
use ratatui_image::picker::{Picker, ProtocolType};
use ratatui_image::{Image, Resize};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (mode, out) = match &args[..] {
        [_, mode, out] => (mode.as_str(), out.as_str()),
        _ => {
            eprintln!("usage: query-options <default|timeout=MS|shm> <OUT>");
            std::process::exit(2);
        }
    };

    let mut terminal = ratatui::init();
    let start = Instant::now();
    let picker = match mode {
        "default" => Picker::from_query_stdio(),
        "shm" => Picker::from_query_stdio_with_options(QueryStdioOptions {
            kitty_shared_memory_object: QueryStdioOptions::probe_kitty_smo(),
            ..QueryStdioOptions::default()
        }),
        timeout => {
            let ms = timeout.strip_prefix("timeout=").and_then(|ms| ms.parse().ok()).expect("timeout=MS");
            Picker::from_query_stdio_with_options(QueryStdioOptions { timeout_ms: ms, ..QueryStdioOptions::default() })
        }
    };
    let query_ms = start.elapsed().as_secs_f64() * 1000.0;

    let mut line = format!("mode={mode} query_ms={query_ms:.2}");
    match &picker {
        Ok(picker) => {
            line += &format!(" protocol={:?} capabilities={:?}", picker.protocol_type(), picker.capabilities());
            if picker.protocol_type() == ProtocolType::Kitty {
                // A 640x640 photo-like picture: noise, so nothing compresses it away.
                let mut seed = 0x2545_f491_u32;
                let picture = RgbImage::from_fn(640, 640, |_, _| {
                    seed ^= seed << 13;
                    seed ^= seed >> 17;
                    seed ^= seed << 5;
                    image::Rgb([seed as u8, (seed >> 8) as u8, (seed >> 16) as u8])
                });
                let area = Rect::new(0, 0, 32, 16);
                let encode = Instant::now();
                let protocol = picker
                    .new_protocol(DynamicImage::ImageRgb8(picture), area.into(), Resize::Fit(None))
                    .expect("encode");
                let encode_ms = encode.elapsed().as_secs_f64() * 1000.0;
                // The frame that sends it: the terminal reads and unlinks a
                // shared memory object only once it gets the escape.
                let draw = Instant::now();
                terminal.draw(|frame| frame.render_widget(Image::new(&protocol), area)).expect("draw");
                let draw_ms = draw.elapsed().as_secs_f64() * 1000.0;
                line += &format!(" encode_ms={encode_ms:.2} draw_ms={draw_ms:.2}");
            }
        }
        Err(e) => line += &format!(" error={e:?}"),
    }
    ratatui::restore();

    let mut file = OpenOptions::new().create(true).append(true).open(out).expect("open OUT");
    writeln!(file, "{line}").expect("write OUT");
}
