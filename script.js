// Initialize an array to store unique values from the third column
const uniqueValues3c = [];
const uniqueValues1c = [];
// Create a table element
const table = document.createElement("table");
const tableContainer = document.getElementById("tableContainer");

// Function to read a CSV file in "Nordic (ISO 8859-10)" encoding and convert it to UTF-8
function handleCSVFile(file) {
    const reader = new FileReader();

    reader.onload = function (e) {
        const contents = e.target.result;


        // Convert the CSV data to UTF-8 encoding
        //budjetti.vm.fi https://budjetti.vm.fi/indox/opendata/ = iso-8859-10
        //Good practice is UTF-8
        const encryptionDecoder = new TextDecoder("utf-8"); 
        const utf8Text = encryptionDecoder.decode(contents);

        const lines = utf8Text.split("\n");



        // Initialize a flag to identify the header row
        let isFirstRow = true;

        // Loop through CSV lines
        lines.forEach((line, index) => {
            const row = document.createElement("tr");
            const cells = line.split(";"); // Use semicolon as the separator

            cells.forEach((cell, cellIndex) => {
                const cellElement = isFirstRow ? document.createElement("th") : document.createElement("td");
                cellElement.textContent = cell.trim();

                // If it's the header row, set the cell as a table header (th)
                if (isFirstRow) {
                    cellElement.scope = "col";
                }

                row.appendChild(cellElement);
            });

            // Add the "Budjettipuu" column to the header and data rows
            if (isFirstRow) {
                // For the header row, add headers
                const budjettipuuHeader = document.createElement("th");
                budjettipuuHeader.textContent = "Budjettipuu";
                row.insertBefore(budjettipuuHeader, row.firstChild);
                const momenttitasoHeader = document.createElement("th");
                momenttitasoHeader.textContent = "Momenttitaso";
                row.insertBefore(momenttitasoHeader, row.firstChild);
            } else {
                // For data rows, calculate and add the "Budjettipuu" value
                const firstColumn = cells[0] ? cells[0].trim() : "";
                const thirdColumn = cells[2] ? cells[2].trim() : "";
                const fifthColumn = cells[4] ? cells[4].trim() : "";
                const budjettipuuCell = document.createElement("td");
                budjettipuuCell.textContent = `${firstColumn}.${thirdColumn}.${fifthColumn}.`;
                row.insertBefore(budjettipuuCell, row.firstChild);

                const momenttitasoCell = document.createElement("td");
                momenttitasoCell.textContent = `3`;
                row.insertBefore(momenttitasoCell, row.firstChild);

                // Store unique values from the first column
                if (cells[0]) {
                    const uniqueValue1 = cells[0].trim();
                    if (!uniqueValues1c.includes(uniqueValue1)) {
                        uniqueValues1c.push(uniqueValue1);
                    }
                    // Store unique values from the third column
                    if (cells[2]) {
                        const uniqueValue3and1 = `${cells[0].trim()}.${cells[2].trim()}`;
                        if (!uniqueValues3c.includes(uniqueValue3and1)) {
                            uniqueValues3c.push(uniqueValue3and1);
                        }
                    }

                }
            }

            table.appendChild(row);

            // After processing the first row, set the flag to false
            if (isFirstRow) {
                isFirstRow = false;
            }
        });

        // Create new rows based on unique values in the third column
        uniqueValues3c.forEach((uniqueValue) => {
            const newRow = createMomenttitaso2(lines, uniqueValue);
            table.appendChild(newRow);
        });

        // Create new rows based on unique values in the first column
        uniqueValues1c.forEach((uniqueValue) => {
            const newRow = createMomenttitaso1(lines, uniqueValue);
            table.appendChild(newRow);
        });

        // Clear previous table and append the new one
        tableContainer.innerHTML = "";
        tableContainer.appendChild(table);
    };

    reader.readAsArrayBuffer(file);
}

// Function to create a new row based on a unique value in the third column
function createMomenttitaso2(lines, uniqueValue) {
    const newRow = document.createElement("tr");

    // Initialize an array to store values for the new row
    const newRowValues = [];

    // Find rows with matching values in the third column
    lines.forEach((line) => {
        const cells = line.split(";");
        if (cells[2] && `${cells[0].trim()}.${cells[2].trim()}` === uniqueValue) {
            newRowValues.push(cells.map((cell) => cell.trim()));
        }
    });

    // Calculate the sums of each cell with matching first and third cell values
    const sums = calculateSumsOfMatchingCells(lines, newRowValues[0][0], newRowValues[0][2]);

    // Fill in values for the new row based on the row beneath it
    if (newRowValues.length > 0) {
        newRowValues[0].forEach((value, cellIndex) => {
            const cellElement = document.createElement("td");
            if (cellIndex >= 7 && cellIndex <= 19) {
                // Set the sum of the corresponding cell with matching first and third cell values
                cellElement.textContent = sums[cellIndex - 7]; // Adjust the index
            } else if (cellIndex === 4 || cellIndex === 5) {
                // Ensure the fifth, and sixth cells are empty
                cellElement.textContent = "";
            } else {
                cellElement.textContent = value;
            }
            newRow.appendChild(cellElement);
        });
    }

    // Add the "Budjettipuu" column to the new row
    const budjettipuuCell = document.createElement("td");
    budjettipuuCell.textContent = `${newRowValues[0][0]}.${newRowValues[0][2]}.`;
    newRow.insertBefore(budjettipuuCell, newRow.firstChild);

    const momenttitasoCell = document.createElement("td");
    momenttitasoCell.textContent = `2`;
    newRow.insertBefore(momenttitasoCell, newRow.firstChild);

    return newRow;
}

// Function to create a new row based on a unique value in the third column
function createMomenttitaso1(lines, uniqueValue) {
    const newRow = document.createElement("tr");

    // Initialize an array to store values for the new row
    const newRowValues = [];

    // Find rows with matching values in the third column
    lines.forEach((line) => {
        const cells = line.split(";");
        if (cells[0] && cells[0].trim() === uniqueValue) {
            newRowValues.push(cells.map((cell) => cell.trim()));
        }
    });

    // Calculate the sums of each cell with matching first and third cell values
    const sums = calculateSumsOfMatchingCells(lines, newRowValues[0][0], null);

    // Fill in values for the new row based on the row beneath it
    if (newRowValues.length > 0) {
        newRowValues[0].forEach((value, cellIndex) => {
            const cellElement = document.createElement("td");
            if (cellIndex >= 7 && cellIndex <= 19) {
                // Set the sum of the corresponding cell with matching first and third cell values
                cellElement.textContent = sums[cellIndex - 7]; // Adjust the index
            } else if (cellIndex === 2 || cellIndex === 3 || cellIndex === 4 || cellIndex === 5) {
                // Ensure the third, fourth, fifth, and sixth cells are empty
                cellElement.textContent = "";
            } else {
                cellElement.textContent = value;
            }
            newRow.appendChild(cellElement);
        });
    }

    // Add the "Budjettipuu" column to the new row
    const budjettipuuCell = document.createElement("td");
    budjettipuuCell.textContent = `${newRowValues[0][0]}.`;
    newRow.insertBefore(budjettipuuCell, newRow.firstChild);

    const momenttitasoCell = document.createElement("td");
    momenttitasoCell.textContent = `1`;
    newRow.insertBefore(momenttitasoCell, newRow.firstChild);

    return newRow;
}

// Function to calculate the sums of specified cells (8th to 20th) with matching first and third cell values
function calculateSumsOfMatchingCells(lines, firstCellValue, thirdCellValue) {
    const sums = Array(13).fill(0); // Initialize an array for cells 8 to 20

    lines.forEach((line) => {
        const cells = line.split(";");
        if (cells[0] && cells[0].trim() === firstCellValue && cells[2] && (cells[2].trim() === thirdCellValue || thirdCellValue === null)) {
            for (let cellIndex = 7; cellIndex <= 19; cellIndex++) {
                if (cells[cellIndex]) {
                    sums[cellIndex - 7] += parseFloat(cells[cellIndex]);
                }
            }
        }
    });

    return sums;
}


// Add an event listener to the file input element
const fileInput = document.getElementById("csvFileInput");
fileInput.addEventListener("change", (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
        handleCSVFile(selectedFile);
    }
});

// Add an HTML input field for the new values
const newValuesInput = document.getElementById("newValuesInput");

// Add a button to trigger the synchronization
const syncButton = document.getElementById("syncButton");
syncButton.addEventListener("click", syncTable);

// Function to synchronize the table based on new values
function syncTable() {
    const newValues = newValuesInput.value.split("\n").map((value) => value.trim());

    // Find values that are in newValues but not in the current "Budjettipuu" column
    const missingValues = newValues.filter((newValue) => {
        // Extract the "Budjettipuu" value from the newValue
        const budjettipuuValue = newValue.split(".")[0];

        // Check if it doesn't exist in the current "Budjettipuu" values
        return !uniqueValues1c.includes(budjettipuuValue);
    });

    // Create empty table rows for missing values
    missingValues.forEach((missingValue) => {
        const newRow = createEmptyRow(missingValue);
        table.appendChild(newRow);
    });
}

// Function to create an empty row based on missingValues input
function createEmptyRow(missingValues) {
    const newRow = document.createElement("tr");

    // Split the missingValues string by "." to count the number of segments
    const momenttitasoValue = missingValues.split(".").length - 1;

    // Add the "Budjettipuu" column to the new row
    const budjettipuuCell = document.createElement("td");
    budjettipuuCell.textContent = missingValues;
    newRow.insertBefore(budjettipuuCell, newRow.firstChild);

    const momenttitasoCell = document.createElement("td");
    momenttitasoCell.textContent = momenttitasoValue.toString();
    newRow.insertBefore(momenttitasoCell, newRow.firstChild);

    return newRow;
}