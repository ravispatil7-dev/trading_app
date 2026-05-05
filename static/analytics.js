<link rel="stylesheet" href="/static/style.css">

<div class="dashboard">

    <!-- SIDEBAR -->
    <div class="sidebar">
        <img src="/static/logo.png" width="180">

        <h3>📊 Analytics</h3>

        <a href="/dashboard">Dashboard</a>
        <a href="/analytics">Analytics</a>
        <a href="/profile">Profile</a>
        <a href="/logout">Logout</a>
    </div>

    function loadAnalytics() {
    fetch("/api/history")
    .then(res => res.json())
    .then(data => {

        let total = data.length;
        let wins = 0;
        let profit = 0;
        let balance = 10000;

        let chartData = [];
        let tableHTML = "";

        data.forEach(trade => {

            profit += trade.profit;
            balance += trade.profit;

            if (trade.profit > 0) wins++;

            chartData.push(balance);

            tableHTML += `
                <tr>
                    <td>${trade.time}</td>
                    <td>${trade.signal}</td>
                    <td>${trade.entry}</td>
                    <td>${trade.exit}</td>
                    <td style="color:${trade.profit >= 0 ? 'lime' : 'red'}">
                        ${trade.profit}
                    </td>
                </tr>
            `;
        });

        let winrate = total > 0 ? (wins / total * 100).toFixed(1) : 0;

        document.getElementById("total").innerText = total;
        document.getElementById("winrate").innerText = winrate + "%";
        document.getElementById("profit").innerText = profit.toFixed(2);
        document.getElementById("balance").innerText = balance.toFixed(2);

        document.getElementById("historyTable").innerHTML = tableHTML;

        drawChart(chartData);
    });
}

function drawChart(data) {
    new Chart(document.getElementById("chart"), {
        type: 'line',
        data: {
            labels: data.map((_, i) => i + 1),
            datasets: [{
                label: "Equity",
                data: data,
                borderWidth: 2,
                tension: 0.3
            }]
        }
    });
}

loadAnalytics();