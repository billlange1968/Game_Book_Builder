# Game Book Builder  

This Python GUI app helps you build "Choose Your Own Adventure" style game books. 


## GAME BOOK STORY BUILDER – QUICK GUIDE  
================================================  

1. STORY METADATA  
   Enter your story title and author name at the top.  

2. PASSAGES  
   • Each "passage" is one chunk of story text (like a page in a CYOA book).  
   • Click [ + ] in the Passages panel to create a new one.  
   • Click a passage in the list to edit it.  
   • The ★ symbol marks the starting passage (the first page of the PDF).  

3. WRITING A PASSAGE  
   • Give it a short title (optional – used in the PDF heading).  
   • Write your story text in the large box.  
     Separate paragraphs with a blank line.  
   • Click "Save Passage Changes" or switch passages – it auto-saves.  

4. CHOICES / BRANCHES  
   • Click "+ Add Choice" to add a decision the reader can make.  
   • Fill in the choice text (e.g. "Open the mysterious door").  
   • Select the Passage ID the choice leads to from the dropdown.  
   • Passages with NO choices are treated as endings.  

5. EXPORTING TO PDF  
   • "Export PDF (Randomized)" – shuffles passage order so the page  
     numbers are unpredictable (classic CYOA feel!). The start passage
     is always page 1.  
   • "Export PDF (In Order)" – passages appear in creation order.  
   • After export you'll see which passage ended up on which page.  

6. SAVING / LOADING  
   • File → Save / Save As to save as a .cyoa file (JSON format).  
   • File → Open to reload a saved story.  

## TIPS  
----  
• Plan your story as a flowchart first – sketch nodes and arrows on paper.  
• Keep passage text 100-300 words for readability.  
• Test your story by tracing all paths to make sure every branch leads
  somewhere (or ends intentionally).  
