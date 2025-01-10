export const ChatWindow = () => {
    return (
        <div className="flex items-center justify-center h-screen w-screen">
            <div className="flex flex-col border border-white h-5/6 w-5/6">
                
                <div className="border border-white flex-grow"></div>
                
                <div className="flex items-center justify-center gap-3 p-2 border-t border-white">
                    <input 
                        type="text" 
                        placeholder="Type your message..." 
                        className="flex-grow p-2 border border-gray-300 rounded bg-black text-white"
                    />
                    <button className="px-4 py-2 bg-black border border-white text-white rounded hover:bg-gray-600">
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
};
