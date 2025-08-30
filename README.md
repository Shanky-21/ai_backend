# 🚀 Business Insights AI - LangGraph Workflow System

An intelligent business analytics platform that automatically analyzes your data files and provides actionable insights using AI-powered workflows.

## 📊 Overview

Business Insights AI is a FastAPI-based application that transforms raw business data into meaningful insights through an automated AI workflow. Upload your CSV/Excel files with a business description, and get comprehensive analysis, visualizations, and actionable recommendations.

### 🎯 Key Features

- **🤖 AI-Powered Analysis**: Uses Azure OpenAI (GPT-4) to understand your business context
- **📈 Automated Insights**: Generates custom Python analysis code for your specific data
- **🔒 Safe Code Execution**: Secure sandboxed environment for running AI-generated code
- **📊 Data Visualization**: Automatically creates charts and graphs
- **🔄 LangGraph Workflow**: Orchestrated multi-step analysis pipeline
- **📝 Business-Friendly Reports**: Converts technical results into executive summaries
- **🌐 REST API**: Easy integration with web applications
- **📋 Multiple File Support**: Analyzes multiple CSV/Excel files together

## 🏗️ Architecture

### Workflow Pipeline
```
📁 File Upload → 🔍 Data Analysis → 🧠 Business Understanding → 🗂️ File Mapping → ⚡ Insight Generation
```

### Core Components

1. **Data Analysis Node**: Extracts metadata and samples from uploaded files
2. **Business Understanding Node**: AI analyzes business context and suggests help areas
3. **File Mapping Node**: Maps files to specific insights based on relevance
4. **Insight Generation Node**: Generates and executes custom analysis code

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.12
- **AI/ML**: Azure OpenAI (GPT-4), LangChain, LangGraph
- **Data Processing**: Pandas, NumPy
- **Visualizations**: Matplotlib, Seaborn
- **Monitoring**: LangSmith (optional)
- **Environment**: Virtual environments, python-dotenv

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Azure OpenAI API access
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install langgraph langchain-openai langsmith pandas matplotlib seaborn numpy fastapi uvicorn python-multipart python-dotenv openpyxl
   ```

4. **Configure environment variables**
   ```bash
   # Create .env file
   echo "AZURE_OPENAI_API_KEY=your-azure-openai-api-key" > .env
   echo "AZURE_OPENAI_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/" >> .env
   echo "LANGCHAIN_TRACING_V2=true" >> .env
   ```

5. **Add your data files**
   ```bash
   mkdir -p resources/data
   # Copy your CSV/Excel files to resources/data/
   ```

### Running the Application

#### Option 1: Test with Sample Data
```bash
# Run complete system test
python test_complete_system.py

# View detailed insights
python view_insights.py

# Extract visualizations
python show_visualizations.py
```

#### Option 2: Start the API Server
```bash
# Start FastAPI server
python start_server.py

# Server will be available at http://localhost:8000
```

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Analyze Business Data
```http
POST /analyze
Content-Type: multipart/form-data

Parameters:
- files: Multiple CSV/Excel files
- business_description: Text description of your business
```

**Example Response:**
```json
{
  "status": "success",
  "business_understanding": "Retail business focused on customer satisfaction...",
  "insights": [
    {
      "title": "Customer Satisfaction Analysis",
      "priority": "high",
      "files_used": ["customer_data.csv"],
      "analysis_results": {
        "metrics": {"satisfaction_score": 4.2},
        "key_findings": ["Customer satisfaction is above average"],
        "recommendations": ["Focus on resolving complaints faster"]
      }
    }
  ],
  "total_insights": 1
}
```

## 📊 Sample Analysis Output

```
🔍 INSIGHT #1: Customer Satisfaction Analysis
Status: success | Priority: high
Files Used: customer_interactions_100.csv, inventory_data.csv

📈 Analysis Results:
  Metrics:
    total_interactions: 100
    average_satisfaction: 2.8
    resolution_rate: 25%
  
  Key Findings:
    - Top interaction types: In-Person, Social Media, Chat
    - 75% of interactions remain unresolved
    - 1 inventory item below reorder point
  
  Recommendations:
    - Focus on resolving customer interactions
    - Implement better inventory management

💼 Business Insights:
  Executive Summary: Analysis shows opportunities for improvement in customer service resolution rates and inventory management.
```

## 📁 Project Structure

```
ai_backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and environment variables
│   ├── types.py             # TypedDict definitions
│   ├── utils.py             # Utility functions
│   ├── workflow_nodes.py    # LangGraph workflow nodes
│   ├── ai_workflow.py       # Workflow orchestration
│   ├── analysis_engine.py   # Code generation and execution
│   └── run_server.py        # Server startup script
├── tests/
│   └── test_basic_workflow.py  # Workflow testing
├── resources/
│   └── data/                   # Data files directory
├── visualizations/             # Generated charts (auto-created)
├── requirements.txt
├── start_server.py            # Main server entry point
├── test_complete_system.py    # System testing
├── view_insights.py           # Insight viewer
├── show_visualizations.py     # Visualization extractor
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Yes |
| `LANGCHAIN_API_KEY` | LangSmith API key | No |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing | No |

### Supported File Types

- **CSV**: `.csv`
- **Excel**: `.xlsx`, `.xls`

### File Size Limits

- Maximum file size: 50MB per file
- No limit on number of files

## 🛡️ Security Features

- **Sandboxed Code Execution**: AI-generated code runs in a restricted environment
- **File Type Validation**: Only allows CSV and Excel files
- **Timeout Protection**: Prevents long-running code execution
- **No Network Access**: Generated code cannot access external resources
- **Temporary File Cleanup**: Automatically removes uploaded files

## 📈 Example Use Cases

### Retail Business
- **Customer Analysis**: Satisfaction scores, interaction patterns
- **Inventory Management**: Stock levels, reorder recommendations
- **Sales Performance**: Revenue trends, product analysis

### E-commerce
- **User Behavior**: Click-through rates, conversion analysis
- **Product Performance**: Best sellers, inventory turnover
- **Customer Service**: Support ticket analysis, resolution times

### Manufacturing
- **Production Metrics**: Output analysis, quality control
- **Supply Chain**: Vendor performance, delivery times
- **Cost Analysis**: Material costs, operational efficiency

## 🚨 Troubleshooting

### Common Issues

1. **Environment Variables Not Set**
   ```bash
   # Check environment
   python check_env.py
   ```

2. **Import Errors**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

3. **File Not Found Errors**
   ```bash
   # Ensure data files are in resources/data/
   ls -la resources/data/
   ```

4. **API Key Issues**
   ```bash
   # Verify .env file
   cat .env
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Azure OpenAI** for powerful language models
- **LangChain/LangGraph** for workflow orchestration
- **FastAPI** for the excellent web framework
- **Pandas** for data manipulation capabilities

## 📞 Support

For support, questions, or feature requests:
- Open an issue on GitHub
- Contact the development team
- Check the troubleshooting section above

---

**Built with ❤️ for better business insights through AI**
