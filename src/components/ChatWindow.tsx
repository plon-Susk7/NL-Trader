import {useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

export const ChatWindow = () => {

    const [socket,setSocket] = useState<any>(null);
    const [messages,setMessages] = useState<string[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = async () =>{
        const message = inputRef.current?.value.trim();
        if(message && socket){
            socket.emit("message",message);
            inputRef.current!.value = "";
        }
        
    }

    useEffect(()=>{
        // Need to replace the hardcoded URL with one in environment variable
        const socketInstance = io("http://127.0.0.1:5000");
        setSocket(socketInstance);

        socketInstance.on("connect",()=>{
            console.log("Connected to the server");
        })

        socketInstance.on("message",(data)=>{
            setMessages((prevMessages)=>[...prevMessages,data]);
            console.log(data);
        })

        // cleaning up component on unmount
        return () => {
            socketInstance.disconnect();
        }
    },[])

    return (
        <div className="flex items-center justify-center h-screen w-screen">
            <div className="flex flex-col border border-white h-5/6 w-5/6">
                
                <div className="border border-white flex-grow overflow-y-auto">

                    {messages && messages.map((message,index)=>(
                        <div key={index} className="flex flex-col p-2 m-2 border rounded-lg border-white inline-block max-w-max">
                            {message}
                            </div>
                    ))}
                </div>
                
                <div className="flex items-center justify-center gap-3 p-2 border-t border-white">
                    <input 
                        type="text"
                        ref={inputRef} 
                        placeholder="Type your message..." 
                        className="flex-grow p-2 border border-gray-300 rounded bg-black text-white"
                    />
                    <button onClick={()=>handleSubmit()} className="px-4 py-2 bg-black border border-white text-white rounded hover:bg-gray-600">
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
};
