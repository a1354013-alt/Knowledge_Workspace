with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 改進 #3：修正角色變更重入庫的 log 文案
old_code = """                # 【新增】logging：記錄文件審核通過事件
                logger.info(
                    f"APPROVED doc_id={doc_id} by={token_data['sub']}"
                )
            except Exception as e:
                # 【新增】logging：記錄向量庫入庫失敗
                logger.error(
                    f"VECTOR_INSERT_FAIL doc_id={doc_id}"
                )
                # 【重要】先清掉可能殘留的 chunk，再回滚 DB 狀態
                delete_from_vector_db(doc_id)
                db.update_document(doc_id, approved=old_approved, is_active=old_is_active, allowed_roles=old_allowed_roles)
                raise HTTPException(status_code=500, detail=f"更新角色旗標失敗: {str(e)}")"""

new_code = """                # 【改進】logging：記錄角色變更重入庫事件（不是審核通過）
                logger.info(
                    f"REINDEX doc_id={doc_id} reason=roles_changed by={token_data['sub']}"
                )
            except Exception as e:
                # 【新增】logging：記錄向量庫入庫失敗
                logger.error(
                    f"VECTOR_INSERT_FAIL doc_id={doc_id}"
                )
                # 【重要】先清掉可能殘留的 chunk，再回滚 DB 狀態
                delete_from_vector_db(doc_id)
                db.update_document(doc_id, approved=old_approved, is_active=old_is_active, allowed_roles=old_allowed_roles)
                raise HTTPException(status_code=500, detail=f"更新角色旗標失敗: {str(e)}")"""

content = content.replace(old_code, new_code)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 改進 #3 完成")
