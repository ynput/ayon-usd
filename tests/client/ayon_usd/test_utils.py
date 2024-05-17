# test_utils.py
import hashlib
import zipfile
from client.ayon_usd import utils


def test_validate_file_checksum(file_info, tmp_path):
    # Create a temporary file
    file_path = tmp_path / file_info['filename']
    file_path.write_text("Hello, World!")

    # Update the checksum to match the file's content
    file_info['checksum'] = hashlib.md5(file_path.read_bytes()).hexdigest()

    assert utils.validate_file_checksum(str(file_path), file_info['checksum'], file_info['checksum_algorithm'])


def test_extract_zip_file(file_info, tmp_path):
    # Create a temporary zip file
    zip_path = tmp_path / file_info['filename']
    with zipfile.ZipFile(str(zip_path), 'w') as zipf:
        zipf.writestr('test.txt', 'Hello, World!')

    # Extract the zip file
    extract_dir = tmp_path / 'extracted'
    utils.extract_zip_file(str(zip_path), str(extract_dir))

    # Check that the extracted file exists
    assert (extract_dir / 'test.txt').exists()


def test_file_info_endpoint(
        printer_session,
        installed_addon,
        ayon_server_session,
        ayon_connection_env):

    server_url, api_key = ayon_connection_env
    session = ayon_server_session
    version = installed_addon

    response = session.get(f"{server_url}/api/addons/usd/{version}/files_info")
    assert response.status_code == 200
