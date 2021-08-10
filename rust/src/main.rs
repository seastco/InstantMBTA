
#[tokio::main]
async fn main() -> Result<(), reqwest::Error> {
    let echo_json = reqwest::Client::new();
    echo_json.get("https://api-v3.mbta.com/lines")
        .send()
        .await?
        .json()
        .await?;

    println!("{:#?}", echo_json);
    Ok(())
}