//! Screener interface + Tier 1 reference rule engine (stub).
//!
//! The `Screener` trait is the stable boundary every validator ships behind.
//! Different validators can bring different models; they all implement this
//! trait. See `docs/specs/training-pipeline.md` §Interface for third-party
//! models.

use aegis_types::{AddressProfile, ContractProfile, Flag, ScreeningResult, Tier, TxFeatureRow};
use async_trait::async_trait;

#[async_trait]
pub trait Screener: Send + Sync {
    async fn screen(
        &self,
        tx: &TxFeatureRow,
        sender: Option<&AddressProfile>,
        target: Option<&ContractProfile>,
    ) -> ScreeningResult;
}

/// Reference Tier 1 rule engine. Starts empty — rules get seeded from known
/// exploit patterns over time (see `docs/specs/training-pipeline.md`
/// §Backtesting).
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
    pub score_bp: u16,
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
    ) -> ScreeningResult {
        let mut reasons = Vec::new();
        let mut worst = Flag::Green;
        let mut max_score = 0u16;

        for rule in &self.rules {
            if let Some(hit) = rule.evaluate(tx, sender, target) {
                reasons.push(format!("{}: {}", rule.name(), hit.reason));
                if flag_rank(hit.flag) > flag_rank(worst) {
                    worst = hit.flag;
                }
                if hit.score_bp > max_score {
                    max_score = hit.score_bp;
                }
            }
        }

        ScreeningResult {
            tx_hash: tx.tx_hash,
            flag: worst,
            score_bp: max_score,
            tier: Tier::One,
            reasons,
        }
    }
}

fn flag_rank(f: Flag) -> u8 {
    match f {
        Flag::Green => 0,
        Flag::Yellow => 1,
        Flag::Orange => 2,
        Flag::Red => 3,
    }
}
