'use client';
import {useEffect,useRef} from 'react';
import {X} from 'lucide-react';
export function Dialog({title,children,onClose}:{title:string;children:React.ReactNode;onClose:()=>void}){const ref=useRef<HTMLDialogElement>(null);useEffect(()=>{const dialog=ref.current;dialog?.showModal();return()=>dialog?.close()},[]);return <dialog ref={ref} className="modal" aria-label={title} onCancel={onClose} onClick={e=>{if(e.target===e.currentTarget)onClose()}}><div className="section-heading"><h2>{title}</h2><button aria-label="Close dialog" className="icon-button" onClick={onClose}><X size={20}/></button></div>{children}</dialog>}
