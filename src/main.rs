use anyhow::Result;
use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    pubkey::Pubkey,
    signature::{read_keypair_file, Keypair, Signer},
    transaction::VersionedTransaction,
};
use std::{str::FromStr, time::Duration};
use tokio::time::sleep;
use log::{info, error};
use reqwest::Client;
use zeromq::Socket;
use zeromq::SocketSend;
use zeromq::SocketRecv;

const RPC_URL: &str = "https://api.mainnet-beta.solana.com";
const KEYPAIR_PATH: &str = "bot_keypair.json";

#[tokio::main]
async fn main() -> Result<()> {
    std::env::set_var("RUST_LOG", "info");
    env_logger::init();

    let rpc = RpcClient::new_with_commitment(RPC_URL.to_string(), CommitmentConfig::confirmed());
    // Basic connectivity check
    info!("🚀 SNIPER ONLINE. WAITING FOR BRAIN...");
    
    let mut socket = zeromq::ReqSocket::new();
    socket.connect("tcp://127.0.0.1:5555").await?;

    loop {
        let heartbeat = serde_json::json!({ "type": "HEARTBEAT" });
        if let Err(e) = socket.send(heartbeat.to_string().into()).await {
             error!("Brain disconnect: {}", e);
             sleep(Duration::from_secs(5)).await;
             continue;
        }
        let _ = socket.recv().await?;
        sleep(Duration::from_secs(1)).await;
    }
}
