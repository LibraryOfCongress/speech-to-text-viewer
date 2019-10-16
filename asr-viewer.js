let $$ = (selector, scope = document) => {
    return [...scope.querySelectorAll(selector)];
};

let player;
let playerContainer = document.querySelector("#player");
let transcriptSearchText = document.querySelector("#transcript-search");
let availableTranscripts = document.querySelector("#available-transcripts");
let transcriptContainer = document.querySelector("#transcript");

function displayItem(itemId) {
    let itemElement = availableTranscripts.querySelector(
        `[data-item-id="${itemId}"]`
    );

    if (!itemElement) {
        console.warn(
            "Couldn't find an option matching selected item ID:",
            itemId
        );
        return;
    }

    document.body.dataset.displayItem = itemId;

    let transcriptUrl = itemElement.dataset.transcriptUrl;
    let itemUrl = itemElement.dataset.itemUrl;
    let mediaType = itemElement.dataset.mediaType;
    let mediaSourceUrl =
        itemElement.dataset.mediaStreamSrc ||
        itemElement.dataset.mediaMasterSrc;

    let subtitleUrl = transcriptUrl
        .replace("results", "webvtt")
        .replace(".json", ".vtt");
    let title = itemElement.title;

    document.location.hash = "#" + itemElement.dataset.itemId;

    initializePlayer(playerContainer, mediaType, mediaSourceUrl, subtitleUrl);

    displayTranscript(transcriptContainer, transcriptUrl, itemUrl, title);
}

function removeChildren(element) {
    while (element.firstChild) {
        element.firstChild.remove();
    }
}

function displayTranscript(transcriptContainer, transcriptUrl, itemUrl, title) {
    let cardTitle = transcriptContainer.querySelector(".card-title");
    cardTitle.textContent = "Loading:" + transcriptUrl;

    let transcriptBody = transcriptContainer.querySelector("tbody");

    removeChildren(transcriptBody);

    fetch(transcriptUrl)
        .then(response => {
            return response.json();
        })
        .then(data => {
            removeChildren(cardTitle);
            var titleLink = document.createElement("a");
            titleLink.target = "_blank";
            titleLink.textContent = `${title} (${data.jobName})`;
            titleLink.href = itemUrl;

            cardTitle.append(titleLink);

            renderTranscript(data.results, transcriptBody);
        });
}

function renderTranscript(results, tableBody) {
    let lastTime = 0;
    let items = results.items;

    let row, timeCell, textCell;

    for (const item of items) {
        // We parse time values into floating-point numbers which will be set on
        // the element itself for JavaScript access and exposed rounded to one
        // place in the element's data attributes for display using CSS

        let startTime = parseFloat(item.start_time);
        let endTime = parseFloat(item.end_time);

        // Some transcripts have punctuation values which lack time codes and,
        // in all observed cases, accompany a previous item which does have
        // timing information.

        if (isNaN(startTime)) {
            if (row && row.endTime) {
                startTime = row.endTime;
            } else {
                console.warn("Unexpected item without a start time:", item);
            }
        }

        if (isNaN(endTime)) {
            if (row && row.endTime) {
                endTime = row.endTime;
            } else {
                console.warn("Unexpected item without an end time:", item);
            }
        }

        if (!row || startTime - lastTime > 1.5) {
            row = document.createElement("tr");
            row.className = "timecode";
            row.startTime = row.dataset.startTime = startTime;
            row.endTime = row.dataset.endTime = endTime;
            tableBody.append(row);

            timeCell = document.createElement("th");
            timeCell.className = "timecode";
            timeCell.startTime = startTime;
            timeCell.dataset.startTime = startTime.toFixed(1);
            row.append(timeCell);

            textCell = document.createElement("td");
            row.append(textCell);
        }

        timeCell.endTime = endTime;
        timeCell.dataset.endTime = endTime.toFixed(1);
        row.endTime = row.dataset.endTime = endTime;

        if (item.alternatives.length > 0) {
            // The format allows more than one alternative but this has not been
            // observed in the wild:
            let alternative = item.alternatives[0];

            let span = document.createElement("span");
            span.classList.add("timecode", item.type);
            span.textContent = alternative.content;

            if (alternative.confidence) {
                let roundedConfidence = Math.round(
                    parseFloat(alternative.confidence) * 10
                );

                // This value is an integer used by the CSS to shade less confident words:
                span.dataset.confidence = roundedConfidence.toFixed(0);
            }

            // We'll set these values directly on the element so floating point
            // comparisons can be made without requiring any string parsing in
            // the highlighting update path
            span.startTime = startTime;
            span.endTime = endTime;

            if (item.start_time) {
                span.title = item.alternatives
                    .map(i => {
                        let formated = item.start_time + "s: " + i.content;
                        if (i.confidence) {
                            formated +=
                                " (" +
                                (100 * parseFloat(i.confidence)).toFixed(1) +
                                "%)";
                        }
                        return formated;
                    })
                    .join(", ");
            }

            textCell.append(span);
        }

        lastTime = endTime;
    }
}

function loadAllTranscripts() {
    fetch("index.json")
        .then(response => {
            return response.json();
        })
        .then(data => {
            let tBody = availableTranscripts.querySelector("tbody");

            Object.entries(data)
                .sort((a, b) => {
                    return a[1].title.localeCompare(b[1].title);
                })
                .forEach(([k, v]) => {
                    // We'll create new table rows for the available transcripts table which contain data attributes which other JS will use to load the actual transcript when selected:
                    let row = document.createElement("tr");

                    row.value = k;
                    row.dataset.itemId = k;

                    row.dataset.transcriptUrl = "results/" + k + ".json"; // FIXME: put this in the JSON!
                    row.dataset.itemUrl = v.item_url;
                    row.dataset.mediaType = v.media_stream_url.match(/[.]mp4$/)
                        ? "video"
                        : "audio";
                    row.dataset.mediaMasterSrc = v.media_master_url;
                    row.dataset.mediaStreamSrc = v.media_stream_url;
                    row.dataset.language = v.language;

                    row.title = v.title;

                    let idCell = document.createElement("th");
                    let titleCell = document.createElement("td");
                    idCell.textContent = k;
                    titleCell.textContent = v.title;
                    row.append(idCell);
                    row.append(titleCell);

                    tBody.append(row);
                });

            let itemId = document.location.hash.replace("#", "");
            if (itemId) {
                $$("tr", availableTranscripts).filter(element => {
                    if (element.dataset.itemId == itemId) {
                        displayItem(itemId);
                    }
                });
            }
        });
}

function initializePlayer(
    playerContainer,
    tagName,
    mediaSourceUrl,
    subtitleUrl
) {
    removeChildren(playerContainer);

    player = document.createElement(tagName);

    player.autoplay = true;
    player.preload = "metadata";
    player.controls = true;
    player.src = mediaSourceUrl;

    let subtitleTrack = document.createElement("track");
    subtitleTrack.label = subtitleTrack.kind = "subtitles";
    subtitleTrack.type = "text/vtt";
    subtitleTrack.src = subtitleUrl;
    player.append(subtitleTrack);

    playerContainer.append(player);

    player.addEventListener("timeupdate", () => {
        let currentTime = player.currentTime;

        $$(".highlighted").forEach(element =>
            element.classList.remove("highlighted")
        );
        $$(".timecode").forEach(element => {
            if (
                element.startTime <= currentTime &&
                element.endTime >= currentTime
            ) {
                element.classList.add("highlighted");
            }
        });
    });
}

transcriptSearchText.addEventListener("focus", () => {
    document.body.classList.add("search-active");
});

transcriptSearchText.addEventListener("input", () => {
    let searchText = transcriptSearchText.value.trim().toLocaleLowerCase();
    if (!searchText) {
        availableTranscripts.querySelectorAll("[hidden]").forEach(element => {
            element.removeAttribute("hidden");
        });
    } else {
        availableTranscripts
            .querySelectorAll("tr[data-item-id]")
            .forEach(element => {
                // TODO: calculate this once on load
                let elementText = `${element.dataset.itemId} ${element.title}`.toLocaleLowerCase();
                if (elementText.includes(searchText)) {
                    element.removeAttribute("hidden");
                } else {
                    element.setAttribute("hidden", "hidden");
                }
            });
    }

    let itemCount = availableTranscripts.querySelectorAll(
        "tbody tr:not([hidden])"
    ).length;

    availableTranscripts.querySelector(
        "caption"
    ).textContent = `${itemCount} items`;
});

availableTranscripts.addEventListener("click", event => {
    let transcriptId = event.target.parentNode.dataset.itemId;
    if (transcriptId) {
        document.body.classList.remove("search-active");
        displayItem(transcriptId);
    }
});

transcriptContainer.addEventListener("click", event_ => {
    let startTime =
        event_.target.startTime || event_.target.parentNode.startTime;
    if (startTime) {
        player.currentTime = startTime;
        player.play();
    }
});

document.addEventListener("keydown", event => {
    if (event.key == " " && player && event.target != transcriptSearchText) {
        if (player.paused) {
            player.play();
        } else {
            player.pause();
        }

        event.preventDefault();
        return false;
    }
});

loadAllTranscripts();
