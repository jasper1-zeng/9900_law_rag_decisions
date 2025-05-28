from app.api.routes.chat import router as chat_router
from app.api.routes.arguments import router as arguments_router
from app.api.routes.case_chunks import router as case_chunks_router
from app.api.routes.users import router as users_router
from app.api.routes.citation_graph import router as citation_graph_router

__all__ = [
    'chat_router',
    'arguments_router',
    'case_chunks_router',
    'users_router',
    'citation_graph_router',
]
