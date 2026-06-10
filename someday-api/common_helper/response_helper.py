from fastapi.responses import JSONResponse


def create_response(status_code: int, result: dict | list | str) -> JSONResponse:
    if isinstance(result, str):
        result = {"message": result}
    return JSONResponse(status_code=status_code, content=result)
