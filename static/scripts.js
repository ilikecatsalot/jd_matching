document.getElementById('upload-form').onsubmit = async function(event) {
    event.preventDefault();
    const jdName = document.getElementById('jd_name').value;
    const nameExists = await checkJDName(jdName);
    if (nameExists) {
        alert('Job description name already exists. Please rename your JD.');
        return;
    }
  

    let formData = new FormData(this);

    try {
        let response = await fetch('/', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        let result = await response.json();
        
        let evaluations = result.result;

        //cutoff filter
        const cutoffPercentage = parseFloat(document.getElementById('cutoff_slider').value);
        evaluations = evaluations.filter(evaluation => {
            const matchPercentage = extractMatchPercentage(evaluation.text);
            return matchPercentage >= cutoffPercentage;
        });
        // Extract match percentage and sort the evaluations in descending order
        evaluations.sort((a, b) => {
            const matchPercentageA = extractMatchPercentage(a.text);
            const matchPercentageB = extractMatchPercentage(b.text);
            return matchPercentageB - matchPercentageA; // Sort in descending order
        });

        // let resultHtml = '';
        const regex = /\d+\.(pdf|doc|docx)/g;

        let resultHtml = '<div class="resume-container">';

        // Set HTML content after sorting
        evaluations.forEach(evaluation => {
            let unclean_text = evaluation.text;
            let pattern = /\b\d\.\s|\$/g;
            let text = unclean_text.replace(pattern,'');
        
            // Split the text into strengths and weaknesses parts
            const strengthsPart = text.split(/Weaknesses:/i)[0].trim();
            const weaknessesPart = text.split(/Weaknesses:/i)[1] ? text.split(/Weaknesses:/i)[1].trim() : '';
        
            // Format the strengths part
            let formattedStrengths = strengthsPart
                .replace(/Strengths:/i, '<br><strong>Strengths:</strong><br>') // Bold and color Strengths heading
                .replace(/\*\*(.*?)\*\*/g, '<span style="color: #49e048;"><strong>$1</strong></span>'); // Highlight strengths in green
        
            // Format the weaknesses part
            let formattedWeaknesses = weaknessesPart
                .replace(/\*\*(.*?)\*\*/g, '<span style="color: red;"><strong>$1</strong></span>'); // Highlight weaknesses in red
        
            // Combine formatted strengths and weaknesses
            let formattedText = formattedStrengths + '<br>' + '<br><strong>Weaknesses:</strong><br>' + formattedWeaknesses;
        
            // Apply additional formatting
            formattedText = formattedText
                .replace(/(Match Percentage:\s*\d+(\.\d+)?%?)/gi, '<br><strong>$1</strong><br>')
            // Bold the match percentage
                .replace(/(Name:\s*[^\n]*)/gi, '<br><strong>$1</strong><br>') // Bold the name
                .replace(/(Resume:)/gi, '<br><strong>$1</strong><br>') // Bold the resume
                .replace(regex, '');
        
            let evaluationHtml = `
                <div class="resume-block">
                    <h3>Filename: ${evaluation.filename}</h3>
                    <p>${formattedText}</p>
                    <a href="${evaluation.filepath}" class="view-resume" target="_blank">View Resume</a>
                </div>
            `;
            resultHtml += evaluationHtml;
        });
        
        resultHtml += '</div>'; 

        document.getElementById('result').innerHTML = resultHtml;

    } catch (error) {
        console.error('Error:', error);
    }
};
// Cutoff Update
document.getElementById('cutoff_slider').addEventListener('input', function() {
    document.getElementById('cutoff_value').textContent = `${this.value}%`;
});
// Function to extract match percentage from the evaluation text
function extractMatchPercentage(evaluationText) {
    const match = evaluationText.match(/Match Percentage: (\d+\.?\d*)%/);
    return match ? parseFloat(match[1]) : 0;
}

// Show file upload or text input based on selected option
document.getElementById('jd_file_option').addEventListener('change', function() {
    document.getElementById('jd_file_upload').style.display = 'block';
    document.getElementById('jd_text_box').style.display = 'none';
});

document.getElementById('jd_text_option').addEventListener('change', function() {
    document.getElementById('jd_file_upload').style.display = 'none';
    document.getElementById('jd_text_box').style.display = 'block';
});

// Toggle between new job description and existing JD sections
document.getElementById('use_new_jd').addEventListener('click', function() {
    document.getElementById('new_jd_section').classList.remove('hidden');
    document.getElementById('existing_jd_section').classList.add('hidden');
    document.getElementById('jd_file_upload').classList.remove('hidden');
    document.getElementById('radio_upload').classList.remove('hidden');
    document.getElementById('toggle_hidden').classList.remove('hidden');
});

document.getElementById('load_existing_jd').addEventListener('click', function() {
    document.getElementById('existing_jd_section').classList.remove('hidden');
    document.getElementById('new_jd_section').classList.add('hidden');
    document.getElementById('jd_file_upload').classList.add('hidden');
    loadExistingJDs();  // Fetch and populate existing JDs
});

// Load existing JDs into the dropdown
function loadExistingJDs() {
    fetch('/get_existing_jds')
        .then(response => response.json())
        .then(data => {
            const jdSelect = document.getElementById('jd_select');
            jdSelect.innerHTML = '';
            data.jds.forEach(jd => {
                const option = document.createElement('option');
                option.value = jd.id;
                option.textContent = jd.name;
                jdSelect.appendChild(option);
            });
        });
}

// Load job description content into the textarea
document.getElementById('load_jd_button').addEventListener('click', function() {
    const jdId = document.getElementById('jd_select').value;
    fetch(`/load_jd/${jdId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('jd_name').value = 'Loaded JD';
            document.getElementById('jd_text_option').checked = true;
            document.getElementById('job_description').value = data.content;
            document.getElementById('new_jd_section').classList.remove('hidden');
            document.getElementById('jd_file_upload').classList.add('hidden');
            document.getElementById('radio_upload').classList.add('hidden');
            document.getElementById('toggle_hidden').classList.add('hidden');
            document.getElementById('toggle_hidden').classList.add('hidden');

            
            
            // Ensure the job description textbox is displayed
            document.getElementById('jd_text_box').style.display = 'block';
        });
});

// Delete job description from the database
document.getElementById('delete_jd_button').addEventListener('click', function() {
    const jdId = document.getElementById('jd_select').value;
    if (jdId) {
        fetch(`/delete_jd/${jdId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            alert(data.status);
            loadExistingJDs();  // Refresh the dropdown list
            document.getElementById('job_description').value = ''; // Clear textarea
            document.getElementById('jd_text_box').style.display = 'none'; // Hide textbox
        })
        .catch(error => {
            console.error('Error:', error);
        });
    } else {
        alert('Please select a Job Description to delete.');
    }
});

async function checkJDName(jdName) {
    const response = await fetch('/check_jd_name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ jd_name: jdName }),
    });
    const data = await response.json();
    return data.exists;
}

