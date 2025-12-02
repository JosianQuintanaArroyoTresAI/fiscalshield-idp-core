# 🤖 AI Agent - Read This First!

Before working on Pattern 2 deployments, CHECK:

**📖 [.github/AGENT_INSTRUCTIONS/DOCKER_LAMBDA_DEPLOYMENT.md](.github/AGENT_INSTRUCTIONS/DOCKER_LAMBDA_DEPLOYMENT.md)**

This contains critical information about:
- Why code changes don't deploy automatically
- The correct deployment workflow
- Common mistakes that waste hours
- Real examples from production debugging

**TL;DR for Pattern 2 code changes:**
```bash
source activate-env.sh
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off
./deploy-pattern2-dev.sh
```

Other instructions: [.github/AGENT_INSTRUCTIONS/README.md](.github/AGENT_INSTRUCTIONS/README.md)
