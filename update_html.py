import re
import os

filepath = r"c:\Users\anase\Desktop\user\food_freshness_portal.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace <style>*</style> with <link rel="stylesheet" href="style.css" />
new_content = re.sub(
    r"<style>.*?</style>",
    '<link rel="stylesheet" href="style.css" />',
    content,
    flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated HTML to use style.css")
