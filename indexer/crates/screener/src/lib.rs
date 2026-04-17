//! Screener interface + Tier 1 reference rule engine (stub).
//!
//! The `Screener` trait is the stable boundary every validator ships behind.
//! Matches the `ModelInterface` / `ScreeningInput` / `ScreeningOutput` shape
//! in `docs/specs/byo-model.md`.

use aegis_types::{
    AddressProfile, BasisPoints, ContractProfile, Flag, ScreeningOutput, TxFeatureRow,
};
use alloy_primitives::B256;
use async_trait::async_trait;

#[async_trait]
pub trait Screener: Send + Sync {
    async fn screen(
        &self,
        tx: &TxFeatureRow,
        sender: Option<&AddressProfile>,
        target: Option<&ContractProfile>,
    ) -> ScreeningOutput;
}

/// Reference Tier 1 rule engine. Rules get seeded from the taxonomy in
/// `docs/specs/hack-taxonomy.md` and the Python reference at
/// `scripts/tier1_detector.py`.
pub struct Tier1RuleEngine {
    rules: Vec<Box<dyn Tier1Rule>>,
}

#[async_trait]
pub trait Tier1Rule: Send + Sync {
    fn name(&self) -> &'static str;

    fn evaluate(
        &self,
        tx: &TxFeatureRow,
        sender: Option<&AddressProfile>,
        target: Option<&ContractProfile>,
    ) -> Option<RuleHit>;
}

pub struct RuleHit {
    pub flag: Flag,
    pub confidence_bp: BasisPoints,
    pub reason: String,
}

impl Tier1RuleEngine {
    pub fn new() -> Self {
        Self { rules: Vec::new() }
    }

    pub fn with_rule(mut self, rule: Box<dyn Tier1Rule>) -> Self {
        self.rules.push(rule);
        self
    }
}

impl Default for Tier1RuleEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Screener for Tier1RuleEngine {
    async fn screen(
        &self,
        tx: &TxFeatureRow,
        sender: Option<&AddressProfile>,
        target: Option<&ContractProfile>,
    ) -> ScreeningOutput {
        let mut reasons: Vec<String> = Vec::new();
        let mut worst = Flag::Clear;
        let mut max_conf: BasisPoints = 0;

        for rule in &self.rules {
            if let Some(hit) = rule.evaluate(tx, sender, target) {
                reasons.push(format!("{}: {}", rule.name(), hit.reason));
                if flag_rank(hit.flag) > flag_rank(worst) {
                    worst = hit.flag;
                }
                if hit.confidence_bp > max_conf {
                    max_conf = hit.confidence_bp;
                }
            }
        }

        let snippet: String = reasons.join(" | ").chars().take(200).collect();

        ScreeningOutput {
            flag: worst,
            confidence_bp: max_conf,
            // TODO: real reasoning hash once model spec is pinned.
            reasoning_hash: B256::ZERO,
            reasoning_snippet: snippet,
        }
    }
}

fn flag_rank(f: Flag) -> u8 {
    f as u8
}
