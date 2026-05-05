function loadPosition() {
    fetch("/get_signal")
    .then(res => res.json())
    .then(data => {

        if(!data.trade){
            document.getElementById("signal").innerText = "NO TRADE";
            document.getElementById("profit").innerText = "0";
            return;
        }

        let trade = data.trade;
        let price = data.price;

        let profit = 0;

        if(trade.signal === "BUY"){
            profit = price - trade.entry;
        } else {
            profit = trade.entry - price;
        }

        document.getElementById("signal").innerText = trade.signal;
        document.getElementById("entry").innerText = trade.entry;
        document.getElementById("price").innerText = price;
        document.getElementById("sl").innerText = trade.sl;
        document.getElementById("tp").innerText = trade.tp;

        let profitEl = document.getElementById("profit");
        profitEl.innerText = profit.toFixed(2);

        profitEl.style.color = profit >= 0 ? "lime" : "red";
    });
}

// AUTO REFRESH
setInterval(loadPosition, 2000);

loadPosition();

function closeTrade(){
    fetch("/close_trade")
    .then(res => res.json())
    .then(data => {
        alert("Trade Closed!");
    });
}

if(data.status === "TRADE_CLOSED"){
    alert("Trade Auto Closed: Profit = " + data.trade.profit);
}