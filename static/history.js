let allTrades = [];

function loadHistory() {
    fetch("/api/history")
    .then(res => res.json())
    .then(data => {

        allTrades = data.reverse();

        let search = document.getElementById("search").value.toLowerCase();
        let filter = document.getElementById("filter").value;

        let now = new Date();

        let html = "";

        allTrades.forEach(trade => {

            let tradeDate = new Date(trade.time);

            // ===== FILTER LOGIC =====
            if(filter === "today"){
                if(tradeDate.toDateString() !== now.toDateString()) return;
            }

            if(filter === "week"){
                let diff = (now - tradeDate) / (1000 * 60 * 60 * 24);
                if(diff > 7) return;
            }

            if(filter === "month"){
                if(tradeDate.getMonth() !== now.getMonth()) return;
            }

            // ===== SEARCH =====
            let text = JSON.stringify(trade).toLowerCase();
            if(!text.includes(search)) return;

            html += `
                <tr>
                    <td>${trade.time}</td>
                    <td>${trade.signal}</td>
                    <td>${trade.entry}</td>
                    <td>${trade.exit || "-"}</td>
                    <td>${trade.sl}</td>
                    <td>${trade.tp}</td>
                    <td style="color:${trade.profit >= 0 ? 'lime' : 'red'}">
                        ${trade.profit || 0}
                    </td>
                </tr>
            `;
        });

        document.getElementById("historyTable").innerHTML = html;
    });
}

function downloadCSV() {

    let csv = "Time,Signal,Entry,Exit,SL,TP,Profit\n";

    allTrades.forEach(t => {
        csv += `${t.time},${t.signal},${t.entry},${t.exit},${t.sl},${t.tp},${t.profit}\n`;
    });

    let blob = new Blob([csv], { type: "text/csv" });
    let url = URL.createObjectURL(blob);

    let a = document.createElement("a");
    a.href = url;
    a.download = "trade_history.csv";
    a.click();
}

// AUTO REFRESH
setInterval(loadHistory, 3000);
loadHistory();