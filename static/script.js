async function fetchSignal(){

    let res = await fetch('/get_signal');
    let data = await res.json();

    if(data.error){
        console.log(data.error);
        return;
    }

    document.getElementById("price").innerText = data.price;
    document.getElementById("signal").innerText = data.signal;
    document.getElementById("entry").innerText = data.entry;
    document.getElementById("sl").innerText = data.sl;
    document.getElementById("tp").innerText = data.tp;

    if(data.signal !== "WAIT"){
        alert("🚨 " + data.signal + " SIGNAL");
    }
}

setInterval(fetchSignal, 5000);

async function fetchSignal(){

    let res = await fetch('/get_signal');
    let data = await res.json();

    if(data.error){
        console.log(data.error);
        return;
    }

    document.getElementById("price").innerText = data.price;
    document.getElementById("sentiment").innerText = data.sentiment;

    for (let tf in data.timeframes){
        document.getElementById("rsi_" + tf).innerText = data.timeframes[tf].rsi;
        document.getElementById("atr_" + tf).innerText = data.timeframes[tf].atr;
    }
}

setInterval(fetchSignal, 1000);

function updateDateTime() {
    let now = new Date();

    let date = now.toLocaleDateString();
    let time = now.toLocaleTimeString();

    document.getElementById("date").innerText = "📅 " + date;
    document.getElementById("time").innerText = "⏰ " + time;
}

// update every second
setInterval(updateDateTime, 1000);
updateDateTime();
function loadSignal() {
    fetch("/get_signal")
    .then(res => res.json())
    .then(data => {

        if(data.error){
            console.log(data.error);
            return;
        }

        // ===== PRICE + SENTIMENT =====
        document.getElementById("price").innerText = data.price;
        document.getElementById("sentiment").innerText = data.sentiment;

        // ===== RSI / ATR =====
        let tf = data.timeframes;
        for(let key in tf){
            document.getElementById("rsi_" + key).innerText = tf[key].rsi;
            document.getElementById("atr_" + key).innerText = tf[key].atr;
        }

        // ===== TRADE =====
        if(data.trade){
            document.getElementById("trade_status").innerText = data.status;
            document.getElementById("trade_signal").innerText = data.trade.signal;
            document.getElementById("trade_entry").innerText = data.trade.entry;
            document.getElementById("trade_sl").innerText = data.trade.sl;
            document.getElementById("trade_tp").innerText = data.trade.tp;

            // PROFIT LIVE
            let profit = 0;
            if(data.trade.signal === "BUY"){
                profit = data.price - data.trade.entry;
            } else {
                profit = data.trade.entry - data.price;
            }

            document.getElementById("trade_profit").innerText = profit.toFixed(2);
        } else {
            document.getElementById("trade_status").innerText = "NO TRADE";
        }

    });
}

// ===== CLOSE TRADE =====
function closeTrade(){
    fetch("/close_trade")
    .then(res => res.json())
    .then(data => {
        alert("Trade Closed");
    });
}

function updateConfidence(conf){

    document.getElementById("confidence").innerText = conf + "%";

    // Rotate (max 180deg)
    let deg = (conf / 100) * 180;
    document.getElementById("fill").style.transform = "rotate(" + deg + "deg)";

    // Color zones
    let color = "#ef4444"; // red
    let label = "LOW";

    if(conf >= 70){
        color = "#22c55e"; // green
        label = "HIGH";
    }
    else if(conf >= 50){
        color = "#facc15"; // yellow
        label = "MEDIUM";
    }

    document.querySelectorAll(".fill").forEach(el=>{
        el.style.backgroundColor = color;
    });

    document.getElementById("conf_label").innerText = label;
}
let conf = data.confidence || 0;
updateConfidence(conf);

// AUTO REFRESH
setInterval(loadSignal, 2000);
loadSignal();