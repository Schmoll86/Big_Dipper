#!/bin/bash
# Run this script after creating the GitHub repository

REPO_URL="https://github.com/Schmoll86/Little_Dipper.git"

echo "🌙 Pushing Little Dipper to GitHub..."
echo "Repository: $REPO_URL"
echo

git remote add origin $REPO_URL
git branch -M main
git push -u origin main

echo
echo "✅ Successfully pushed to GitHub!"
echo "View at: https://github.com/Schmoll86/Little_Dipper"
