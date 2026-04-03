from http import HTTPStatus

AUTH_HEADERS = {"X-API-Key": "test-key"}

# ── Health ─────────────────────────────────────────────────────────────────────

def test_health_check(client):
    # GET /health should always return 200 with a status payload
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# ── Auth ───────────────────────────────────────────────────────────────────────

def test_valid_api_key(file_client):
    # A correct API key in the X-API-Key header should be accepted
    response = file_client.get("/api/files", headers=AUTH_HEADERS)
    assert response.status_code == 200

def test_invalid_api_key(file_client):
    # A wrong API key should be rejected with 403 Forbidden
    response = file_client.get("/api/files", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

# ── List files ─────────────────────────────────────────────────────────────────

def test_list_files(file_client, tmp_path):
    # Both files and subdirectories should appear in the listing
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "subdir").mkdir()

    response = file_client.get("/api/files/", headers=AUTH_HEADERS)
    assert response.status_code == 200

    names = [item["name"] for item in response.json()]
    assert "notes.txt" in names
    assert "subdir" in names

# ── Read file ──────────────────────────────────────────────────────────────────

def test_read_file(file_client, tmp_path):
    # Reading an existing UTF-8 file should return its content
    (tmp_path / "hello.txt").write_text("hello world")

    response = file_client.get("/api/files/content?file=hello.txt", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["content"] == "hello world"

def test_read_nonexistent_file(file_client):
    # Requesting a file that doesn't exist should return 404
    response = file_client.get("/api/files/content?file=ghost.txt", headers=AUTH_HEADERS)
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_read_directory_as_file(file_client, tmp_path):
    # Trying to read a directory as a file should return 400
    (tmp_path / "mydir").mkdir()
    response = file_client.get("/api/files/content?file=mydir", headers=AUTH_HEADERS)
    assert response.status_code == HTTPStatus.BAD_REQUEST

def test_read_non_utf8_file(file_client, tmp_path):
    # Binary files that can't be decoded as UTF-8 should return 400
    (tmp_path / "binary.bin").write_bytes(bytes([0xFF, 0xFE, 0x00]))
    response = file_client.get("/api/files/content?file=binary.bin", headers=AUTH_HEADERS)
    assert response.status_code == HTTPStatus.BAD_REQUEST

# ── Write file ─────────────────────────────────────────────────────────────────

def test_write_file(file_client, tmp_path):
    # Writing a file should create it on disk with the correct content
    response = file_client.put(
        "/api/files/content",
        json={"path": "new.txt", "content": "written by test"},
        headers=AUTH_HEADERS
    )
    assert response.status_code == 200
    assert (tmp_path / "new.txt").read_text() == "written by test"

def test_write_to_directory(file_client, tmp_path):
    # Writing to a path that is already a directory should return 400
    (tmp_path / "adir").mkdir()
    response = file_client.put(
        "/api/files/content",
        json={"path": "adir", "content": "oops"},
        headers=AUTH_HEADERS
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST

# ── Delete ─────────────────────────────────────────────────────────────────────

def test_delete_file(file_client, tmp_path):
    # Deleting a file should remove it from disk
    (tmp_path / "bye.txt").write_text("delete me")

    response = file_client.delete("/api/files/?path=bye.txt", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert not (tmp_path / "bye.txt").exists()

def test_delete_directory(file_client, tmp_path):
    # Deleting a directory should remove it and all its contents recursively
    d = tmp_path / "olddir"
    d.mkdir()
    (d / "file.txt").write_text("inside")
    response = file_client.delete("/api/files/?path=olddir", headers=AUTH_HEADERS)
    assert response.status_code == HTTPStatus.OK
    assert not d.exists()

# ── Security ───────────────────────────────────────────────────────────────────

def test_path_traversal_blocked(file_client):
    # Paths that escape the base directory (e.g. ../../etc/passwd) must be blocked
    response = file_client.get("/api/files/content?file=../../etc/passwd", headers=AUTH_HEADERS)
    assert response.status_code == HTTPStatus.FORBIDDEN

# ── Download ───────────────────────────────────────────────────────────────────

def test_download_file(file_client, tmp_path):
    # Downloading a file should return its bytes with content-disposition attachment
    (tmp_path / "report.txt").write_text("download me")
    response = file_client.get("/api/files/download?file=report.txt&api_key=test-key")
    assert response.status_code == HTTPStatus.OK
    assert response.content == b"download me"
    assert "attachment" in response.headers["content-disposition"]

def test_download_invalid_api_key(file_client):
    # A wrong API key on the download endpoint should return 403
    response = file_client.get("/api/files/download?file=report.txt&api_key=wrong")
    assert response.status_code == HTTPStatus.FORBIDDEN

def test_download_directory(file_client, tmp_path):
    # Trying to download a directory should return 400
    (tmp_path / "mydir").mkdir()
    response = file_client.get("/api/files/download?file=mydir&api_key=test-key")
    assert response.status_code == HTTPStatus.BAD_REQUEST

# ── Upload ─────────────────────────────────────────────────────────────────────

def test_upload_file(file_client, tmp_path):
    # Uploading a file should write it to disk with the correct bytes
    file_content = b"uploaded content"
    response = file_client.post(
        "/api/files/upload",
        data={"path": ""},
        files={"files": ("upload.txt", file_content, "text/plain")},
        headers=AUTH_HEADERS
    )
    assert response.status_code == HTTPStatus.OK
    assert (tmp_path / "upload.txt").read_bytes() == file_content
