# Automated Resume Customizer (ARC)

An intelligent system that tailors your resume to specific job applications by analyzing the job description and selecting the most relevant content from your base resume.

## Overview

ARC creates customized resumes through a multi-step workflow:

1. Researches the company to enhance the job description with additional context
2. Selects relevant responsibility and accomplishment groups for each role in your resume
3. Constructs polished, targeted sentences that highlight your relevant experience
4. Reviews sentences for clarity, grammar, and readability
5. Reviews the overall content for relevance and narrative flow
6. Creates a tailored resume summary that aligns with the job requirements

## Requirements

- Python 3.8+
- An OpenAI API key for core functionality
- A Perplexity API key (default) or Tavily API key for company research

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/openfinesse/arc.git
   cd arc
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your API keys:

   ```
   OPENAI_API_KEY=your_openai_api_key
   PERPLEXITY_API_KEY=your_perplexity_api_key
   # Or alternatively:
   # TAVILY_API_KEY=your_tavily_api_key
   # RESEARCH_API_PROVIDER=tavily
   ```

## Preparing Your Resume

ARC uses a modular YAML format for your base resume, which allows the system to mix and match content effectively. You have two options:

1. **Create a resume.yaml file manually** following the structure in the example files
2. **Let ARC create one for you** by running the system without specifying a resume file

For the second option, ARC will run a modularization process to create a structured YAML file from your inputs.

## Usage

Run ARC with a job description to create a customized resume:

```bash
python -m src.main --job-description path/to/job_description.txt --output path/to/output/resume.md
```

For a specific resume file:

```bash
python -m src.main --resume path/to/your/resume.yaml --job-description path/to/job_description.txt --output path/to/output/resume.md
```

### Command Line Arguments

- `--job-description`: Path to the job description text file (required)
- `--output`: Path to save the customized resume (required)
- `--resume`: Path to your resume YAML file (optional, defaults to `input/resume.yaml`)
- `--skip-modularizer`: Skip checking for and creating a modular resume (optional)

## Resume YAML Format

Your resume should follow this structure:

```yaml
basics:
  name: "Your Name"
  email: "your.email@example.com"
  # Other personal details
  
work:
  - title_variables:
      - "Job Title"
      - "Alternative Title"
    start_date: "Jan 2020"
    end_date: "Present"
    company: "Company Name"
    location: "City, State"
    responsibilities_and_accomplishments:
      group_1:
        modular_sentence: "Accomplished {X} by doing {Y} which resulted in {Z}"
        variables:
          X:
            - "option 1 for X" 
            - "option 2 for X"
          Y:
            - "option 1 for Y"
            - "option 2 for Y"
          Z:
            - "option 1 for Z"
            - "option 2 for Z"
      # More groups...
  # More work experiences...
```

See `input/resume_example.yaml` for a complete example.

## Output

ARC generates a customized resume in Markdown format, which you can:

- Convert to PDF using tools like Pandoc
- Import into word processors
- Use with Markdown-based resume templates

The output includes a tailored professional summary and selectively highlighted experience based on the job requirements.
