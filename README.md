# Resume Customizer

An agentic workflow system that customizes resumes for specific job applications based on a base resume in YAML format and a job description.

## Overview

This system follows a multi-step workflow to create tailored resumes:

1. Researches the company using perplexity's sonar-pro model to augment the job description
2. Determines which roles to include from your base resume
3. Selects appropriate responsibility/accomplishment groups for each role
4. Constructs and reviews sentences for readability and grammar
5. Reviews overall content for relevance and narrative coherence
6. Creates a resume summary tailored to the job and company

## Requirements

- Python 3.8+
- OpenAI API key (for most agents)
- Perplexity API key (for company research)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/resume-customizer.git
   cd resume-customizer
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. Set up your API keys as environment variables:
   ```bash
   export OPENAI_API_KEY="your_openai_api_key"
   export PERPLEXITY_API_KEY="your_perplexity_api_key"
   ```

2. Prepare your base resume in YAML format (see `resume.yaml` for an example)

3. Save your job description in a text file

## Usage

Run the system with:

```bash
python src/main.py --resume resume.yaml --job-description job_description.txt --output customized_resume.md
```

The system will:
1. Load your base resume data from the YAML file
2. Process the job description from the text file
3. Execute the customization workflow
4. Generate a tailored resume in Markdown format

### Example Structure

The resume data in YAML should follow this structure:

```yaml
basics:
  name: "First Last"
  email: "example@test.com"
  # ... other personal details
  
work:
  - title_variations:
      - "Job Title 1"
      - "Alternative Title"
    start_date: "Jan 2020"
    end_date: "Present"
    company:
      - "Company Name"
    location: "City, State"
    responsibilities_and_accomplishments:
      group_1:
        original_sentence: "Accomplished X by doing Y which resulted in Z"
        base_sentences:
          - "Accomplished {X} by doing {Y} which resulted in {Z}"
        variations:
          X:
            - "option 1 for X" 
            - "option 2 for X"
          Y:
            - "option 1 for Y"
            - "option 2 for Y"
          Z:
            - "option 1 for Z"
            - "option 2 for Z"
      # ... more groups
  # ... more work experiences
```

## Architecture

The system uses a modular architecture with specialized agents:

- `CompanyResearcher`: Researches company info and enhances job description
- `RoleSelector`: Selects relevant roles from your work experience
- `GroupSelector`: Selects relevant responsibility groups for each role
- `SentenceConstructor`: Constructs tailored sentences
- `SentenceReviewer`: Reviews sentences for grammar and readability
- `ContentReviewer`: Reviews overall content for relevance and narrative
- `SummaryGenerator`: Creates a tailored resume summary

Each agent can be used independently or as part of the orchestrated workflow.

## Customization

You can modify the agent parameters in their respective files under `src/agents/`.

## License

MIT License 