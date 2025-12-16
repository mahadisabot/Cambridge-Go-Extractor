import re

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>...</head>
<body>
    <h1>Index of /rkdjwhqowc/books_data/9781108796606-54.1.1/9781108796606_resources/</h1>
    <table>
        <tr><th>Name</th><th>Last modified</th><th>Size</th></tr>
        <tr><td><a href="../">../</a></td><td>-</td><td>-</td></tr>
        <tr><td><a href="9781108796606_Answer_Key.zip">9781108796606_Answer_Key.zip</a></td><td>2021-09-01 12:00</td><td>5.2M</td></tr>
        <tr><td><a href="styles/">styles/</a></td><td>-</td><td>-</td></tr>
        <tr><td><a href="worksheet.pdf">worksheet.pdf</a></td><td>2021-09-02 10:00</td><td>1.1M</td></tr>
    </table>
</body>
</html>
"""

def parse_resources(html, base_url):
    resources = []
    # Regex to find hrefs that are files (not parent dir or subdirs ideally)
    # Simple href="([^"]+)"
    links = re.findall(r'href="([^"]+)"', html)
    
    for link in links:
        if link == "../" or link.endswith("/"): continue # Skip dirs
        
        full_url = base_url.rstrip('/') + '/' + link
        resources.append({
            'name': link,
            'url': full_url
        })
        
    return resources

base = "https://elevate-s3.cambridge.org/.../resources/"
res = parse_resources(html_content, base)
print(res)
