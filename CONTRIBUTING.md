# Contributing to Lotus Trader

Thank you for your interest in contributing to Lotus Trader! This document provides guidelines for contributing to the project.

## 🎯 **How to Contribute**

### **1. Fork and Clone**
```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/Lotus_Trader.git
cd Lotus_Trader
```

### **2. Set Up Development Environment**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your configuration
```

### **3. Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### **4. Make Your Changes**
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### **5. Test Your Changes**
```bash
# Run tests
pytest tests/

# Run linting
flake8 src/
black --check src/
mypy src/
```

### **6. Submit a Pull Request**
- Push your branch to your fork
- Create a pull request against the main branch
- Provide a clear description of your changes

## 📋 **Code Standards**

### **Python Style**
- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black default)
- Use meaningful variable and function names

### **Documentation**
- Add docstrings to all functions and classes
- Update README.md if adding new features
- Include examples for complex functionality

### **Testing**
- Write tests for all new functionality
- Aim for >80% test coverage
- Use descriptive test names
- Test both success and failure cases

## 🏗️ **Architecture Guidelines**

### **Organic Intelligence Principles**
- Follow the organic team architecture
- Use the AD_strands database for communication
- Implement resonance calculations (φ, ρ, θ)
- Embrace uncertainty-driven exploration

### **Team Structure**
- New agents should extend the appropriate base class
- Use the enhanced agent base classes for CIL integration
- Follow the strand-braid learning system
- Implement proper error handling and logging

## 🐛 **Reporting Issues**

### **Bug Reports**
When reporting bugs, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### **Feature Requests**
For feature requests, please include:
- Clear description of the feature
- Use case and motivation
- Proposed implementation approach
- Any relevant examples or references

## 🔒 **Security**

### **Security Issues**
- **DO NOT** create public issues for security vulnerabilities
- Email security issues to: [security@yourdomain.com]
- Include detailed information about the vulnerability
- Allow time for response before public disclosure

### **Code Security**
- Never commit API keys or secrets
- Use environment variables for sensitive data
- Follow secure coding practices
- Validate all inputs

## 📝 **Commit Messages**

Use clear, descriptive commit messages:
```
feat: add new risk assessment agent
fix: resolve database connection timeout
docs: update API documentation
test: add tests for motif integration
refactor: simplify resonance calculations
```

## 🎯 **Development Workflow**

### **1. Planning**
- Check existing issues and discussions
- Propose major changes in discussions first
- Break large features into smaller PRs

### **2. Development**
- Write tests first (TDD approach)
- Make small, focused commits
- Keep PRs small and focused
- Update documentation as you go

### **3. Review Process**
- All PRs require review
- Address review feedback promptly
- Ensure CI/CD checks pass
- Squash commits before merging

## 🚀 **Getting Help**

### **Questions and Discussion**
- Use GitHub Discussions for questions
- Check existing documentation first
- Be specific about your use case
- Provide relevant code examples

### **Community Guidelines**
- Be respectful and inclusive
- Help others learn and grow
- Share knowledge and best practices
- Follow the code of conduct

## 📄 **License**

By contributing to Lotus Trader, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to Lotus Trader! Together we're building the future of organic intelligence trading systems.
