// ===============================
// NFL Ticker Loader
// ===============================

async function loadTicker() {
    try {
        const res = await fetch("/nfl-ticker/");
        const data = await res.json();

        const tickerDiv = document.getElementById("nfl-ticker");

        tickerDiv.innerHTML = data.ticker
            .map(item => `<span><a href="${item.link}" target="_blank">${item.title}</a></span>`)
            .join("");
    } catch (err) {
        console.error("Ticker error:", err);
    }
}

// Load ticker immediately
loadTicker();

// Refresh ticker every 60 seconds
setInterval(loadTicker, 60000);


// ===============================
// Lineup Generator
// ===============================

const runOptimizerButton = document.getElementById("runOptimizer");

if (runOptimizerButton) {
    runOptimizerButton.addEventListener("click", async () => {
        const playersSection = document.querySelector(".players");

        // Show loading message
        playersSection.innerHTML = `
            <h2>Generating lineups...</h2>
            <p>Please wait.</p>
        `;

        try {
            const response = await fetch('/optimal-lineup/');
            const data = await response.json();

            // Handle backend errors
            if (!response.ok) {
                playersSection.innerHTML = `
                    <h2>Optimizer Error</h2>
                    <p>${data.error || "No valid lineup generated."}</p>
                `;
                return;
            }

            // No lineups returned
            if (!data.lineups || data.lineups.length === 0) {
                playersSection.innerHTML = `
                    <h2>No Lineups Found</h2>
                    <p>The optimizer did not return any valid lineups.</p>
                `;
                return;
            }

            // Render lineups
            playersSection.innerHTML = `
                <h2>Generated DK Classic Lineups</h2>

                ${data.lineups.map((lineup, index) => `
                    <div class="lineup-card">
                        <h3>Lineup ${index + 1}</h3>

                        <p>
                            Projection:
                            <strong>${Number(lineup.total_points).toFixed(2)}</strong>
                        </p>
                        <p>
                            Salary:
                            <strong>$${Number(lineup.salary).toLocaleString()}</strong>
                        </p>
                        <p>
                            Remaining:
                            <strong>$${Number(lineup.remaining_salary).toLocaleString()}</strong>
                        </p>

                        <ul class="player-list">
                            ${Object.entries(lineup.players).map(([slot, player]) => `
                                <li class="player-card">
                                    <div class="player-name">${slot}: ${player.name}</div>
                                    <div class="player-position">${player.position} — ${player.team}</div>
                                    <div class="player-stats">
                                        <span>Salary: $${Number(player.salary).toLocaleString()}</span>
                                        <span>Proj: ${Number(player.proj).toFixed(2)}</span>
                                        <span>Status: ${player.status || "ACTIVE"}</span>
                                    </div>
                                </li>
                            `).join("")}
                        </ul>
                    </div>
                `).join("")}
            `;
        } catch (error) {
            playersSection.innerHTML = `
                <h2>Request Failed</h2>
                <p>Could not reach the optimizer API.</p>
                <p>${error}</p>
            `;
        }
    });
}
