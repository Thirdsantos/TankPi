import requests

def notify_task_complete(document_id: str):
    """
    Notify the backend that a scheduled feeding task is complete.

    Args:
        document_id (str): The Firestore document ID of the completed task.
    """
    try:
        url = f"https://aquacare-5cyr.onrender.com/task_complete/{document_id}"
        print(f"[TASK COMPLETE] Sending POST request to: {url}")

        response = requests.post(url, timeout=10)
        response.raise_for_status()  # Raises exception for 4xx/5xx responses

        print(f"[TASK COMPLETE] ✅ Successfully marked task {document_id} as complete.")
        return {"status": "success", "message": f"Task {document_id} marked complete."}

    except requests.exceptions.RequestException as e:
        print(f"[TASK COMPLETE ERROR] ❌ Failed to notify backend: {e}")
        return {"status": "error", "message": str(e)}
