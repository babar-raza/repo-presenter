pub struct AhoCorasick {
    pub patterns: Vec<String>,
}

impl AhoCorasick {
    pub fn new() -> Self {
        AhoCorasick { patterns: Vec::new() }
    }
}
