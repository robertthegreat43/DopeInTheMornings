// ===============================
// Dope In The Mornings — JS Engine
// ===============================

// --- Collapsible Panel (Instant Toggle) ---
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector(".collapsible-toggle");
    const content = document.querySelector(".collapsible-content");

    if (toggle && content) {
        toggle.addEventListener("click", () => {
            const isVisible = content.style.display === "block";
            content.style.display = isVisible ? "none" : "block";
            toggle.textContent = isVisible ? "Show Serialized Entries" : "Hide Serialized Entries";
        });
    }
});

// --- Generate Optimized Lineups ---
const generateButton = document.getElementById("generateOptimized");
const optimizedOutput = document.getElementById("optimized-output");

if (generateButton) {
    generateButton.addEventListener("click", async () => {

        optimizedOutput.innerHTML = `
            <h2>Generating optimized lineups...</h2>
            <p>Please wait while the neural network processes your data.</p>
        `;

        try {
            const response = await fetch("/generate-optimized-lineups/");
            const data = await response.json();

            if (!response.ok || !data.lineups) {
                optimizedOutput.innerHTML = `
                    <h2>Error</h2>
                    <p>${data.error || "Could not generate optimized lineups."}</p>
                `;
                return;
            }

            optimizedOutput.innerHTML = `
                <h2>Optimized Lineups</h2>
                ${data.lineups.map((lineup, index) => `
                    <div class="lineup-card">
                        <h3>Lineup ${index + 1}</h3>
                        <p><strong>Score:</strong> ${Number(lineup.score).toFixed(4)}</p>

                        <ul class="player-list">
                            ${Object.entries(lineup.players).map(([slot, player]) => `
                                <li class="player-card">
                                    <div class="player-name">${slot}: ${player.name}</div>
                                    <div class="player-position">${player.position} — ${player.team}</div>
                                    <div class="player-stats">
                                        <span>Salary: $${Number(player.salary).toLocaleString()}</span>
                                        <span>Proj: ${Number(player.projection).toFixed(2)}</span>
                                    </div>
                                </li>
                            `).join("")}
                        </ul>
                    </div>
                `).join("")}
            `;
        } catch (err) {
            optimizedOutput.innerHTML = `
                <h2>Request Failed</h2>
                <p>${err}</p>
            `;
        }
    });
}

// --- Load Serialized Entries ---
async function loadSerializedEntries() {
    const container = document.getElementById("serialized-entries");

    if (!container) return;

    container.innerHTML = `<p>Loading serialized entries...</p>`;

    try {
        const response = await fetch("/get-serialized-entries/");
        const data = await response.json();

        if (!response.ok || !data.entries) {
            container.innerHTML = `<p>No serialized entries found.</p>`;
            return;
        }

        container.innerHTML = `
            <h3>Serialized Entries</h3>
            ${data.entries.map(entry => `
                <div class="serialized-card">
                    <pre>${JSON.stringify(entry, null, 2)}</pre>
                </div>
            `).join("")}
        `;
    } catch (err) {
        container.innerHTML = `<p>Error loading entries: ${err}</p>`;
    }
}

// Load serialized entries on page load
loadSerializedEntries();
