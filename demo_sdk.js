const hbsdk = require('./sdk/hbsdk');

function run() {
    // Preparation: Fill out `config/default.json`
    // `access_key` & `secret_key`: Apply for these at www.huobi.com
    // `account_id`: Find your UID after logging in
    // `trade_password`: You may leave this blank initially; required for withdrawals

    // Step 1: Retrieve your `account_id`
    hbsdk.get_account().then(console.log);
    // Take `id` corresponding to `type=spot` from `get_account` response & insert 
    // it into `${account_id_pro}` field within `default.json`

    // Step 2: Retrieve Balance and Open Orders
    // hbsdk.get_balance().then(console.log);
    // hbsdk.get_open_orders('btcusdt').then(console.log);
    
    // Step 3: Trading
    // hbsdk.buy_limit('ltcusdt', 0.01, 0.1);

    // Step 4: Check Order Status
    // hbsdk.get_order(377378515).then(console.log);

    // Step 5: Withdrawal
    // First, set up a secure withdrawal address on the website.
    // hbsdk.withdrawal('0x9edfe04c866d636526828e523a60501a37daf8f6', 'etc', 1);

}

run();