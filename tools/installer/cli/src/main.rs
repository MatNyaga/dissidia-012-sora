//! Test/CI harness: runs exactly what the app runs and prints the same plain-word texts.
//!   sorapatch-cli RELEASE_DIR INPUT_FILE [--out-dir DIR]
//!   sorapatch-cli --check-strings
//! Exit 0 = new file built, 1 = a problem (message printed), 2 = usage / release error.

use sorapatch_core::{build, check_input, plan_output, Problem, Progress, Release, Stage};
use std::path::PathBuf;

const STRINGS_JS: &str = include_str!("../../app/ui/strings.en.js");

/// Every problem code the core can return; each needs err_<code>_title/_body texts.
const CODES: &[&str] = &[
    "not_found", "is_folder", "cant_read", "empty", "archive", "compressed_image", "eboot",
    "not_disc", "other_game", "wrong_region", "incomplete", "already_patched", "older_patch",
    "modified", "no_space", "no_space_late", "cant_write", "build_failed", "cancelled",
];

fn strings() -> serde_json::Value {
    let a = STRINGS_JS.find('{').expect("strings: no {");
    let b = STRINGS_JS.rfind('}').expect("strings: no }");
    serde_json::from_str(&STRINGS_JS[a..=b]).expect("strings.en.js is not valid JSON after '='")
}

fn text(s: &serde_json::Value, key: &str, p: &Problem) -> String {
    let mut t = s[key].as_str().unwrap_or(key).to_string();
    for (k, v) in &p.params {
        t = t.replace(&format!("{{{k}}}"), v);
    }
    t
}

struct Bar {
    last: (Option<Stage>, u64),
}

impl Progress for Bar {
    fn update(&mut self, stage: Stage, done: u64, total: u64) {
        let pct = if total == 0 { 100 } else { done * 100 / total };
        let step = pct / 10 * 10;
        if self.last != (Some(stage), step) {
            self.last = (Some(stage), step);
            println!("progress {stage:?} {pct}%");
        }
    }
    fn cancelled(&self) -> bool {
        false
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let s = strings();
    if args.first().map(String::as_str) == Some("--check-strings") {
        let mut missing = 0;
        for c in CODES {
            for suffix in ["title", "body"] {
                let k = format!("err_{c}_{suffix}");
                if s[&k].as_str().is_none() {
                    println!("missing {k}");
                    missing += 1;
                }
            }
        }
        println!("strings: {} codes, {missing} missing", CODES.len());
        std::process::exit(if missing == 0 { 0 } else { 1 });
    }
    if args.len() < 2 {
        eprintln!("usage: sorapatch-cli RELEASE_DIR INPUT_FILE [--out-dir DIR] | --check-strings");
        std::process::exit(2);
    }
    let rel = Release::load_dir(&PathBuf::from(&args[0])).unwrap_or_else(|e| {
        eprintln!("release: {e}");
        std::process::exit(2)
    });
    let input = PathBuf::from(&args[1]);
    let out_dir = args.iter().position(|a| a == "--out-dir").and_then(|i| args.get(i + 1)).map(PathBuf::from);
    let mut bar = Bar { last: (None, 101) };
    let result = check_input(&rel, &input, &mut bar)
        .and_then(|_| plan_output(&rel, &input, out_dir.as_deref()))
        .and_then(|out| build(&rel, &input, &out, &mut bar));
    match result {
        Ok(out) => {
            println!("OK {}", s["done_title"].as_str().unwrap_or(""));
            println!("output {}", out.display());
        }
        Err(p) => {
            println!("PROBLEM {}", p.code);
            println!("  {}", text(&s, &format!("err_{}_title", p.code), &p));
            println!("  {}", text(&s, &format!("err_{}_body", p.code), &p));
            if !p.detail.is_empty() {
                println!("  detail: {}", p.detail);
            }
            std::process::exit(1);
        }
    }
}
