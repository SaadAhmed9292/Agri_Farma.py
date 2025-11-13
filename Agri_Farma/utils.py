
# utils.py - helpers for pagination and search
from flask import request

def paginate(query, page_param='page', per_page=12):
    page = request.args.get(page_param, 1, type=int)
    per_page = request.args.get('per_page', per_page, type=int)
    items = query.paginate(page=page, per_page=per_page, error_out=False)
    return items

def search_like(model, field, term):
    return model.query.filter(field.ilike(f"%{term}%"))
