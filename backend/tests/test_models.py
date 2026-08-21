from app.models import Base, Conversation, Document, DocumentChunk, Message, User


def test_database_metadata_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "documents",
        "document_chunks",
        "conversations",
        "messages",
    }


def test_model_constraints_and_vector_dimension() -> None:
    users = Base.metadata.tables["users"]
    chunks = Base.metadata.tables["document_chunks"]

    assert users.c.email.nullable is False
    assert any(index.unique and index.name == "ix_users_email" for index in users.indexes)
    assert chunks.c.embedding.type.dim == 384
    assert any(constraint.name == "uq_document_chunks_document_index" for constraint in chunks.constraints)


def test_expected_foreign_keys_and_delete_actions() -> None:
    documents = Base.metadata.tables["documents"]
    chunks = Base.metadata.tables["document_chunks"]
    conversations = Base.metadata.tables["conversations"]
    messages = Base.metadata.tables["messages"]

    assert next(iter(documents.c.uploaded_by.foreign_keys)).ondelete == "RESTRICT"
    assert next(iter(chunks.c.document_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(conversations.c.user_id.foreign_keys)).ondelete == "RESTRICT"
    assert next(iter(messages.c.conversation_id.foreign_keys)).ondelete == "CASCADE"


def test_expected_orm_relationships_are_configured() -> None:
    assert User.documents.property.back_populates == "uploader"
    assert User.conversations.property.back_populates == "user"
    assert Document.uploader.property.back_populates == "documents"
    assert Document.chunks.property.back_populates == "document"
    assert DocumentChunk.document.property.back_populates == "chunks"
    assert Conversation.messages.property.back_populates == "conversation"
    assert Message.conversation.property.back_populates == "messages"
