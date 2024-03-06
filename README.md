# ObsidianToHtml
This Python script converts your entire Obsidian vault with markdown documents into HTML documents in a new folder with identical structure. The script uses Pandoc and will convert the following parameters:

1. File name
2. File creation date
3. Meta data "Creation date" from Frontmatter (key: "created") copied to HTML meta key ("created")
4. All note contents
5. Images are embedded in-place
6. Yellow highlights are converted from markdown-style format into HTML-style div tags
7. Code comments are colored correctly

## IMPORTANT

This script makes the following assumptions:
1. All your resources (such as images) are all located in one single folder, for example "_resources" at the top of your vault. 
2. You need to change "source_directory" and "output_directory" in the script. "source_directory" should point at your Obsidian vault folder, "output_directory" should be another, empty folder.
3. You can exclude folders you do not want to process using "excluded_dirs". This is already set to {'_excalidraw', '_resources', '_templates', '.obsidian', '.trash'}.
4. You can modify the HTML template according to your likings, the file is called "template.html".

## EXAMPLES

Here is a simple example showing how elements are converted from Markdown to HTML:

![](media/Example-obsidian.png)

![](media/Example-resulting_html.png)
