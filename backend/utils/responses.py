from fastapi import JSONResponse


def success_response(data=None, message="OK", status=200):
    return JSONResponse(
        status_code=status,
        content={
            "ok": True,
            "data": data or {},
            "error": None,
            "message": message,
        }
    )


def error_response(error_code, status=400, message="An error occurred", data=None):
    return JSONResponse(
        status_code=status,
        content={
            "ok": False,
            "data": data or {},
            "error": error_code,
            "message": message,
        }
    )

