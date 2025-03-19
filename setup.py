from setuptools import setup, find_packages

setup(
    name="osticket_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "netmiko",
        "pydantic",
        "python-dotenv",
        "smolagents",
        "openai",  # Required by OpenRouter
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
            "types-requests",
        ],
    },
    python_requires=">=3.9",
)