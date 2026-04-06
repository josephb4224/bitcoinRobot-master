const moment = require('moment');
const WebSocket = require('ws');
const pako = require('pako');

const WS_URL = 'wss://api.huobi.pro/ws';

var symbols = ['xrpbtc'];

var orderbook = {};

exports.OrderBook = orderbook;

function handle(data) {
    // console.log('received', data.ch, 'data.ts', data.ts, 'crawler.ts', moment().format('x'));
    let symbol = data.ch.split('.')[1];
    orderbook[symbol] = data.tick;
}

function init() {
    var ws = new WebSocket(WS_URL);
    ws.on('open', () => {
        console.log('open');
        // Exercise caution when selecting depth level for merging. Since WebSocket pushes
        // full depth data sets with every update, failure to process this data in a timely
        // manner can easily lead to mssg accumulation & result in market data latency.
        for (let symbol of symbols) {
            ws.send(JSON.stringify({
                "sub": `market.${symbol}.depth.step0`,
                "id": `${symbol}`
            }));
        }
    });
    ws.on('message', (data) => {
        let text = pako.inflate(data, {
            to: 'string'
        });
        let msg = JSON.parse(text);
        if (msg.ping) {
            ws.send(JSON.stringify({
                pong: msg.ping
            }));
        } else if (msg.tick) {
            handle(msg);
        } else {
            console.log(text);
        }
    });
    ws.on('close', () => {
        console.log('close');
        init();
    });
    ws.on('error', err => {
        console.log('error', err);
        init();
    });
}

init();