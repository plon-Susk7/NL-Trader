import {useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { dark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const CodeBlock = (codeString:string) => {
    let cleanCode = codeString.trim().replace("```python","");
    cleanCode = cleanCode.replace("```","");
    return (
        <SyntaxHighlighter language="python" style={dark}>
            {cleanCode}
        </SyntaxHighlighter>
    )
}

export const ChatWindow = () => {

    const [socket,setSocket] = useState<any>(null);
    const [messages,setMessages] = useState<Array<[string, boolean]>>([]); // we'll use true to indicate that the message was sent by the user and false to indicate that the message was received from the server
    const inputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = async () =>{
        const message = inputRef.current?.value.trim();
        if (message) {
            setMessages((prevMessages)=>[...prevMessages,[message,true]]);
            // setMessages((prevMessages) => [...prevMessages, message]);
        }
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
            setMessages((prevMessages)=>[...prevMessages,[data,false]]);
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
                
                <div className="flex flex-col border border-white flex-grow overflow-y-auto">

                    {messages && messages.map((message,index)=>(
                        
                        <div key={index} className={`flex flex-col p-2 m-2 border rounded-lg border-white inline-block max-w-max w-2/3 ${message[1]==false ? "self-start" : "self-end"}`}>
                            {message[0].includes("```python") ? (
                                CodeBlock(message[0])
                            ) : (
                                
                                <div>{message[0]}</div>
                            )}
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
