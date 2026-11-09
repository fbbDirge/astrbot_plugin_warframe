"""Resolve only images attached to this command or its explicit reply, never chat history."""
import asyncio
from types import SimpleNamespace


def chain_of(event):
    return getattr(getattr(event,'message_obj',None),'message',None) or getattr(event,'get_messages',lambda:[])() or []


def kind(segment):
    return (str(segment.get('type','')) if isinstance(segment,dict) else type(segment).__name__).lower()


def images(chain):
    result=[]
    for c in chain:
        if kind(c)!='image':continue
        if isinstance(c,dict):
            data=c.get('data') or c
            # The scanner's existing download/size/security checks still apply.
            c=type('Image',(),{'url':data.get('url'),'file':data.get('file')})()
        result.append(c)
    return result


async def image_event(event):
    chain=chain_of(event)
    found=images(chain)
    if found:return SimpleNamespace(message_obj=SimpleNamespace(message=found),get_messages=lambda:found)  # Current attachment wins.
    replies=[c for c in chain if kind(c)=='reply']
    for reply in replies[:1]:
        quoted=reply.get('chain',[]) if isinstance(reply,dict) else getattr(reply,'chain',[])
        found=images(quoted or [])
        if not found:
            # OneBot may provide an ID without the expanded Reply.chain.
            bot=getattr(event,'bot',None)
            fetch=getattr(bot,'call_action',None)
            rid=(reply.get('data') or reply).get('id') if isinstance(reply,dict) else getattr(reply,'id',None)
            if callable(fetch) and rid is not None:
                try:
                    response=await asyncio.wait_for(fetch(action='get_msg',message_id=rid),10)
                    payload=response.get('data',response)
                    # Respect the current conversation when the platform supplies its scope.
                    group=str(getattr(event,'get_group_id',lambda:'')() or '')
                    remote=str(payload.get('group_id') or '')
                    sender=str(getattr(event,'get_sender_id',lambda:'')() or '')
                    owner=str((payload.get('sender') or {}).get('user_id') or '')
                    if (remote and remote!=group) or (not group and owner and owner!=sender):continue
                    found=images(payload.get('message') or [])
                except Exception:pass
        if found:
            return SimpleNamespace(message_obj=SimpleNamespace(message=found),get_messages=lambda:found)
    return event
