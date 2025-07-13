# Dynamic Handbook Integration – Implementation Plan

## **Vector Database Persistence & Identification Strategy**

To robustly persist multiple handbook vector indexes, assign each handbook a unique identifier and a dedicated storage location. The identifier can be derived from the file’s name or path, but using a hash of the full file path is more reliable to avoid collisions. For example, the code currently computes an MD5 of the handbook file path to get a stable textbook\_id

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L234-L243)

. In the CLI ingest script, it uses the lowercase filename as the ID

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L144-L152)

, which could conflict if two files share a name. We should standardize on one approach (preferably the path-hash). Directory Structure: Organize the vector index files in a separate folder per handbook. For instance, use a root folder like data/vector\_dbs/ (or the existing vector\_cache/) and create a subdirectory named after the handbook’s ID or hash. Inside this subfolder, store the FAISS index, chunk JSON, and metadata JSON for that handbook. For example:

bash

Copy

Edit

data/vector\_dbs/\<handbook\_id\>/index.faiss  

data/vector\_dbs/\<handbook\_id\>/chunks.json  

data/vector\_dbs/\<handbook\_id\>/meta.json


This keeps each handbook’s data isolated and easy to manage. The metadata file should include a content hash of the handbook text to detect changes

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L416-L424)

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L606-L614)

. On selecting a handbook, the system computes its content hash (e.g. MD5 of file text)

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L8-L15)

 and compares it to the stored hash in \<handbook\_id\>/meta.json. If they differ, the handbook has changed and needs re-indexing

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L416-L424)

. Using the content hash for versioning (in metadata) means we can reuse the same handbook ID folder even if content updates – the system will know to rebuild the index in-place when the hash mismatches

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L425)

. This avoids orphaning old indexes while still ensuring up-to-date vectors. In summary, use a stable ID per handbook (like a path-based hash) to name its storage folder, and store a content hash in metadata for change detection. This strategy is efficient: looking up an existing index is a quick file existence check, and content changes are caught via the stored hash without always re-processing the entire file.

## **On-Demand Vectorization & Loading Logic**

We will implement a “check-then-load-or-create” workflow whenever a handbook is selected:

1. Check for Existing Index: When the user chooses a handbook file, the system should determine the handbook’s ID (e.g. hash of path) and check if a vector index already exists. This can be as simple as checking if the index file (e.g. index.faiss) is present in the handbook’s folder. The TextbookVectorDB.index\_textbook method already encapsulates this logic: it sets rebuild\_needed \= False if an index file and metadata exist, then verifies the content hash and chunking params from metadata  
2. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L410-L419)  
3. . If everything matches, it proceeds to load the existing FAISS index and chunks from disk  
4. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L430-L438)  
5. . We should reuse this logic.  
6. Load Existing Index: If the index is present and up-to-date, load it into memory. The index\_textbook method handles loading: it calls FAISS.load\_local on the saved index and reads the chunks/metadata JSON  
7. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L430-L438)  
8. , then sets the active database and active\_textbook\_id. In our integration, after the user selects a handbook, we can instantiate or fetch the global vector\_db and attempt a load. For example: db \= get\_vector\_db(); db.index\_textbook(handbook\_content, textbook\_id) – if the content is unchanged, this will load the saved index rapidly (the progress callback will report “Loading existing index...”  
9. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L432-L439)  
10. ). Alternatively, if we want a quicker check without reading the full content, we could first inspect the metadata file’s hash versus a newly computed hash. But since index\_textbook does this internally, it’s fine to let it read the content once for hashing.  
11. Create If Not Exists or Outdated: If no index is found or the content has changed (or if loading failed), trigger a new indexing. The index\_textbook function will set rebuild\_needed \= True in those cases (e.g. missing index, hash mismatch, or exception loading a corrupt index)  
12. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L426)  
13. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L458)  
14. . We should ensure to call index\_textbook (or its async variant) at the appropriate time. In a synchronous context, calling it directly will perform ingestion; in an async context (like an asyncio-based flow) use await index\_textbook\_async. For instance, the RAG integration script demonstrates this pattern: it reads the handbook file, then calls:  
15. python  
16. Copy  
17. Edit  
18. db \= get\_vector\_db() await db.index\_textbook\_async(handbook\_content, textbook\_id) results \= await db.query\_textbook\_async(textbook\_id, query, top\_k=3)  
     This ensures the index is created on the fly if needed  
19. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L96-L104)  
20. . We should integrate similar calls when a handbook is selected or when beginning the generation phase.  
21. Handle Corrupted or Incomplete Index: If the index files exist but are corrupted or incomplete, index\_textbook will catch exceptions during load and force a rebuild  
22. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L458)  
23. . We can augment this by explicitly checking that all expected files (.faiss, .chunks.json, .meta.json) are present in the folder. If any file is missing or an error occurs, treat it as if no valid index exists – delete any remnants and set rebuild\_needed \= True. The code already logs an exception and continues to rebuild in case of load failure  
24. [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L457)  
25. . We should make sure to propagate those errors to the user (see Error Handling below). Essentially, the logic is: if index present \-\> try load \-\> if load fails \-\> rebuild from scratch. This guarantees the user always gets a good index or a clear error if indexing fails.

In practice, we will modify rag\_integration.py or the workflow code where the handbook is used to incorporate these steps. For example, in the extract\_student\_handbook\_information() function (or wherever we integrate the handbook in the workflow), add something like:

python

Copy

Edit

db \= get\_vector\_db() with open(handbook\_path, 'rb') as f: content\_bytes \= f.read() handbook\_text \= extract\_text\_from\_file(handbook\_path) *\# handle PDF/Markdown extraction* textbook\_id \= hashlib.md5(handbook\_path.encode()).hexdigest() db.index\_textbook(handbook\_text, textbook\_id) *\# loads existing or builds new* relevant\_chunks \= db.query\_textbook(textbook\_id, query, top\_k=5)

This ensures on-demand vectorization. Notably, the index\_textbook call itself will decide whether to actually do the heavy lifting or just load cached data, based on the conditions discussed. By implementing it here, we eliminate the current issue where the workflow tried to query before indexing (and thus got no results)

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L240-L248)

. *(The extract\_text\_from\_file step is important if the handbook is a PDF – see Error Handling below for how we integrate PDF support from ingest\_textbook.py.)*

## **Performance Feedback & UI Integration**

Because indexing a handbook can take time (especially for large PDFs), the UI must give immediate feedback to the user to avoid appearing frozen. We will use the Kivy UI’s status label and progress bar to show the indexing progress:

* Status Messages: Display a status text like “Processing handbook...” as soon as the user selects a handbook and the indexing begins. We can update this text with finer-grained messages reflecting the current stage (e.g. “Analyzing textbook content…”, “Splitting into chunks…”, “Creating vector embeddings…”, etc.). The TextbookVectorDB.index\_textbook already provides these stage messages via its progress\_callback parameter at various milestones  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L399-L407)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L603-L611)  
* . We can pass a callback that takes the message and percent, and in that callback update the status\_label.text on the main thread (using Clock.schedule\_once if needed to marshal back to UI thread). For example, when index\_textbook reports *"Splitting textbook into chunks..." 15%*  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L463-L471)  
* , we set the label text to “Processing Handbook: Splitting into chunks...” and update the progress bar to 15%.  
* Progress Bar: Utilize the existing ProgressBar widget in the Kivy UI to visualize progress. The WorkflowAppLayout in main.py already has status\_label and progress\_bar properties  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L24-L32)  
* . We can bind the progress bar’s value to the percentage reported by the indexing process. As the progress\_callback supplies a percent (0–100), update progress\_bar.value accordingly. For example, during vector creation, the code calls progress\_callback("Creating FAISS vector database...", 65\)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L501-L509)  
*  and later steps up to 80%, 85%, 90%, etc.  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L586-L594)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L603-L611)  
* . These percentages can drive the progress bar smoothly.  
* UI Modality: It’s wise to make the UI semi-modal during indexing to prevent the user from starting the workflow or selecting another file simultaneously. This could be as simple as disabling the “Start” button until indexing is done, or showing a modal overlay. For instance, when indexing starts, disable or grey-out the main form and re-enable it when finished. If Kivy allows, a popup with a message “Indexing handbook, please wait…” could also be used, especially if we cannot easily integrate the progress bar.  
* Asynchronous Execution: To keep the UI responsive, run the vectorization in a background thread or process. The heavy steps (PDF reading, embedding computations) can be offloaded using Python’s concurrent.futures or Kivy’s Clock.schedule\_once with a threaded function. The repository’s HandbookIndexer class suggests using a ProcessPoolExecutor for indexing  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_editor_ui/claude_panel/handbook_indexer.py#L36-L45)  
* , which is a good approach to avoid blocking the main thread. In that case, we’d periodically poll or use the future’s result to update progress (the subprocess can print progress, which we capture, or we use a shared mechanism). Alternatively, using asyncio with loop.run\_in\_executor (as in rag\_integration.py) is another option  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L96-L104)  
* . The key is to ensure UI updates are done on the main thread.  
* Completion Feedback: Once indexing is complete, update the UI one final time. For example, set progress\_bar.value \= 100 and status\_label.text \= "Handbook indexed successfully." (or if not found relevant chunks, still indicate completion). Then the user can proceed with content generation. If indexing is part of the “Start Workflow” sequence, you might integrate it as an initial stage in the workflow progress list (e.g., insert “Indexing Handbook…” as stage 0).

By providing clear visual feedback (message \+ progress bar) during on-the-fly indexing, we keep the user informed and the app feeling responsive, even if the process takes several minutes for large documents. This prevents confusion where the app might otherwise appear frozen.

## **Error Handling for Handbook Processing**

Robust error handling is essential to handle invalid files or failures in the vectorization pipeline:

* Unsupported or Corrupt File: If the user selects a file that we cannot process (e.g. a corrupt PDF or an unsupported format), the system should quickly inform the user. The ingestion logic in ingest\_textbook.py already checks file existence and extension  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L53-L61)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L120-L125)  
* . We will integrate those checks in our UI flow. For example, when a handbook is selected, verify the extension is .pdf or .md (others can be rejected with a UI popup or label message like “Unsupported file type. Please select a PDF or Markdown file.”). If the file is a PDF but text extraction fails (perhaps due to encryption or corruption), our extract function returns None  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L140-L148)  
* . In such cases, we should stop the indexing process and alert the user: e.g. status\_label.text \= "Failed to read handbook file. Please check the file and try again." and log the error. Logging should include exceptions for debugging (the ingest script logs errors from PyPDF2 or pdfminer if they throw  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L86-L95)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L120-L125)  
* ).  
* Vectorization Failures: Even if we can read the text, embedding or indexing might fail (due to out-of-memory, library errors, etc.). The index\_textbook method is wrapped in try/except internally – it logs and raises on failure  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L626-L630)  
* . We should catch any exception from the index\_textbook call in our UI handler. If an exception occurs during indexing, communicate this to the user via the UI and logs. For instance, show a message like “Error: Handbook indexing failed.” possibly with a suggestion (e.g. “Please try again or check the handbook content format.”). Additionally, write the traceback to a log file for developers. In the RAG integration code, if retrieval fails for any reason, it logs the exception and continues without context  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L110-L118)  
* . Similarly, our workflow should fail gracefully – if handbook processing fails, we don’t crash the app. Instead, we proceed with content generation without handbook context, and mark that in the output (perhaps inserting a note that handbook info was unavailable).  
* User Notification: Use the Kivy UI elements to surface errors clearly. Options include a modal popup (e.g. using messagebox or a Kivy Popup) or simply the status label turning red with an error message. Since the app already uses a log panel (the add\_log\_entry mechanism in the workflow), we can leverage that: for example, in process\_row\_for\_phase, they log a “error” entry if handbook extraction fails  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L353-L358)  
* . Ensure that log is visible to the user (perhaps in a UI log console). In addition, setting the status\_label.text to a brief error summary can catch the user’s attention immediately.  
* Logging: In the backend, record detailed error info. The logging should capture file paths, exception messages, and stack traces. This is already partly done: e.g., extract\_student\_handbook\_information catches exceptions and logs logger.error(...) with the exception message  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L281-L289)  
* , and the workflow adds a log entry with Failed to extract information from handbook: {error}  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L355-L358)  
* . We should extend this to cover extraction and indexing failures explicitly. For example, wrap the db.index\_textbook() call in try/except at the UI integration point: on exception, log logger.exception("Handbook indexing failed") and set an error state.

To illustrate, a possible flow:

python

Copy

Edit

try: success \= db.index\_textbook(handbook\_text, textbook\_id, force\_rebuild=False) except Exception as e: logger.exception(f"Vectorization failed for handbook {handbook\_path}: {e}") ui\_status("Error indexing handbook. See logs for details.") *\# Maybe disable handbook usage and continue workflow without it* return if not success: logger.error(f"Indexing reported failure for {handbook\_path}") ui\_status("Handbook could not be processed.") return  
This way, any failure stops using the handbook and clearly informs the user. The UI might then re-enable controls so the user can fix the issue (choose a different file or skip the handbook). By handling errors at each stage (file open, text extract, index build, query), the system remains robust. The user experience should degrade gracefully – if the handbook is unusable, the app should explain the issue and proceed without that context rather than crashing or hanging. All such incidents should be logged for debugging, including stack traces for developers and a user-friendly message for the end-user.

## **Impact on Data Flow (row\_data\_item & Workflow Integration)**

Integrating the handbook selection into the existing workflow requires passing the handbook path from the UI into the content generation logic, and deciding how to store the RAG context. The design will be as follows:

* Passing the Handbook Path: When the user selects a handbook file in the GUI, we store its path in the app configuration (as already done in WorkflowAppLayout.config\["handbook\_path"\] and a boolean use\_handbook flag  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L139-L147)  
* ). This config is then passed into the ui\_settings or similar structure that the workflow uses. In the current workflow code, ui\_settings expects keys like "use\_student\_handbook" and "student\_handbook\_path"  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L338)  
* . We should map our GUI inputs to these keys. For example, set ui\_settings\["use\_student\_handbook"\] \= True if the handbook checkbox is active, and ui\_settings\["student\_handbook\_path"\] \= "/path/to/handbook.pdf". This can be done when starting the workflow (in start\_workflow() before calling into process\_row\_for\_phase). By doing so, each row’s processing function knows a handbook is available and where to find it.  
* Workflow Usage of Handbook (rag\_context): Within process\_row\_for\_phase, during the generation phase, the code already checks for use\_student\_handbook and then calls our extraction function  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L339)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L340-L349)  
* . After obtaining the relevant info from the handbook, it stores it in variables\["student\_handbook\_info"\]  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L341-L349)  
* . The prompt template is then dynamically modified to include this info (inserting a section for “RELEVANT INFORMATION FROM STUDENT HANDBOOK”)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L346-L354)  
* . This design means the *actual handbook content (relevant excerpts)* is injected into the prompt as text, rather than maintaining a complex object. We will continue with this approach. The row\_data\_item for each CSV row will simply contain the extracted text in its variables if available, not a vector DB object.  
* rag\_context Field: Rather than storing a vector DB instance in each row\_data\_item (which is impractical to serialize and unnecessary), we use the handbook path as the reference and load/query the global vector DB on the fly. If we need to refer to this in data structures, we can include the handbook path or ID in the context. For example, we might add row\_data\_item\["rag\_context"\] \= handbook\_path or just rely on the global ui\_settings. Since the vector DB is a singleton (accessed via get\_vector\_db()  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L845-L853)  
* ), any part of the workflow can retrieve it and query the needed handbook by ID. There’s no need to duplicate that object per row. This ensures immutability and consistency – the handbook index in memory is the same for all steps in the run. In fact, once we index the handbook once at the start of the run, subsequent calls to retrieve chunks (for multiple steps/rows) will be fast and reuse the in-memory active\_db (the code switches active\_db only if a different textbook\_id is requested  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L760-L769)  
* ).  
* Multiple Rows & Handbook Reuse: Given the clarification that one handbook is used per run, we will likely index once and use it for all relevant steps. The first row that needs handbook info will trigger the index load/creation; after that, active\_textbook\_id remains set, so additional queries (query\_textbook) skip even the disk load step and go straight to vector search  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L752-L759)  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L761-L770)  
* . This design is efficient for multi-row operations.  
* Data Immersion into Template: The end result of the RAG process – the relevant handbook excerpts – is treated as just another piece of context text. It’s stored in something like student\_handbook\_info within the variables dict and merged into the prompt template. This is safer and simpler than trying to hold a pointer to the vector DB. Once the content is injected, the generation proceeds normally (Claude or the LLM sees the prompt with the relevant sections included). The workflow log can note that handbook info was added. If no relevant info was found or an error occurred, the template either won’t include that section or might include a placeholder note (as in rag\_integration.py where they add a note if no chunks found  
* [GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L124-L132)  
* ).

In summary, we pass the handbook path from the UI to the backend, use it to generate an ID and load/create the vector index, then store only the *textual* output of RAG in the row’s data. The rag\_context is effectively this text. We do *not* store the index or embedding objects in row\_data\_item – those remain in the global TextbookVectorDB instance. This approach keeps row\_data\_item light and serializable (just JSON-friendly data), while the heavy lifting happens behind the scenes. It also aligns with the current workflow pattern of injecting strings into templates

[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L344-L352)

. By addressing each of these points, we will achieve a seamless, dynamic handbook integration: the system will automatically handle indexing and querying the selected handbook, provide responsive feedback during the process, handle errors gracefully, and incorporate the results into content generation without disrupting the existing workflow structure. This makes the RAG system truly plug-and-play for any handbook a user selects, improving the flexibility of the content generation app.  
Citations  
GitHub  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L234-L243)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/workflow.py\#L234-L243](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L234-L243)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L234-L243)  
[ingest\_textbook.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L144-L152)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/ingest\_textbook.py\#L144-L152](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L144-L152)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L144-L152)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L416-L424)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L416-L424](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L416-L424)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L416-L424)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L606-L614)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L606-L614](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L606-L614)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L606-L614)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L8-L15)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L8-L15](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L8-L15)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L8-L15)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L425)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L418-L425](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L425)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L425)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L410-L419)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L410-L419](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L410-L419)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L410-L419)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L430-L438)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L430-L438](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L430-L438)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L430-L438)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L432-L439)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L432-L439](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L432-L439)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L432-L439)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L426)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L418-L426](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L426)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L418-L426)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L458)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L454-L458](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L458)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L458)  
[rag\_integration.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L96-L104)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/rag\_integration.py\#L96-L104](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L96-L104)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L96-L104)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L457)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L454-L457](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L457)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L454-L457)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L240-L248)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/workflow.py\#L240-L248](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L240-L248)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L240-L248)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L399-L407)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L399-L407](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L399-L407)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L399-L407)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L603-L611)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L603-L611](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L603-L611)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L603-L611)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L463-L471)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L463-L471](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L463-L471)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L463-L471)  
[main.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L24-L32)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py\#L24-L32](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L24-L32)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L24-L32)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L501-L509)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L501-L509](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L501-L509)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L501-L509)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L586-L594)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L586-L594](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L586-L594)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L586-L594)  
[handbook\_indexer.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_editor_ui/claude_panel/handbook_indexer.py#L36-L45)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_editor\_ui/claude\_panel/handbook\_indexer.py\#L36-L45](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_editor_ui/claude_panel/handbook_indexer.py#L36-L45)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_editor_ui/claude_panel/handbook_indexer.py#L36-L45)  
[ingest\_textbook.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L53-L61)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/ingest\_textbook.py\#L53-L61](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L53-L61)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L53-L61)  
[ingest\_textbook.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L120-L125)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/ingest\_textbook.py\#L120-L125](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L120-L125)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L120-L125)  
[ingest\_textbook.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L140-L148)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/ingest\_textbook.py\#L140-L148](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L140-L148)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L140-L148)  
[ingest\_textbook.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L86-L95)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/ingest\_textbook.py\#L86-L95](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L86-L95)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/ingest_textbook.py#L86-L95)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L626-L630)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L626-L630](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L626-L630)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L626-L630)  
[rag\_integration.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L110-L118)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/rag\_integration.py\#L110-L118](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L110-L118)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L110-L118)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L353-L358)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L353-L358](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L353-L358)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L353-L358)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L281-L289)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/workflow.py\#L281-L289](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L281-L289)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/workflow.py#L281-L289)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L355-L358)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L355-L358](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L355-L358)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L355-L358)  
[main.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L139-L147)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py\#L139-L147](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L139-L147)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/main.py#L139-L147)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L338)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L330-L338](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L338)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L338)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L339)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L330-L339](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L339)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L330-L339)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L340-L349)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L340-L349](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L340-L349)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L340-L349)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L341-L349)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L341-L349](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L341-L349)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L341-L349)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L346-L354)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L346-L354](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L346-L354)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L346-L354)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L845-L853)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L845-L853](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L845-L853)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L845-L853)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L760-L769)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L760-L769](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L760-L769)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L760-L769)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L752-L759)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L752-L759](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L752-L759)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L752-L759)  
[textbook\_vector\_db.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L761-L770)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/textbook\_vector\_db.py\#L761-L770](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L761-L770)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/textbook_vector_db.py#L761-L770)  
[rag\_integration.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L124-L132)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup\_tools/simplified\_app/rag\_system/rag\_integration.py\#L124-L132](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L124-L132)  
[GitHub](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/showup_tools/simplified_app/rag_system/rag_integration.py#L124-L132)  
[workflow.py](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L344-L352)  
[https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified\_workflow/workflow.py\#L344-L352](https://github.com/helloshowup/hope-clean/blob/9377ebc2bb39c2da666183bf6e2672ed31000e34/simplified_workflow/workflow.py#L344-L352)

