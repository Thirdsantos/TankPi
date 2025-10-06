import uvicorn

# keep aquarium here
aquarium = 1

if __name__ == "__main__":
    # pass aquarium into the app via uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)
