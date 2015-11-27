#include <stdio.h>
#include <string>
#include <iostream>
#include <iomanip>
#include <typeinfo>
#include <netinet/in.h>
#include <netdb.h>
#include <zmq.h>
#include "schema.pb.h"
#include <unistd.h>

namespace gpb = google::protobuf;

namespace
{
    const char* g_appName = NULL;
    const char* const DEFAULT_ZMQ_ENDPOINT = "tcp://localhost:7779";
    const char* const DEFAULT_ZMQ_SUB_FILTER = "";
    
    void usage()
    {
        printf("\n");
        printf("Usage: %s [options]\n", g_appName);
        printf("Options:\n");
        printf("  -e <endpoint>  ZMQ endpoint to connect/bind to. Default: %s\n", DEFAULT_ZMQ_ENDPOINT);
        printf("  -f <filter>    Message filter to apply on a ZMQ_SUB socket. Default: %s\n",
               strlen(DEFAULT_ZMQ_SUB_FILTER) ? DEFAULT_ZMQ_SUB_FILTER : "<empty>");
        printf("  -b             Listen for ZMQ endpoint on port 7779. Default: connect\n");
        printf("\n");
        exit(1);
    }

    std::ostream& printIndent(std::ostream& os, int indent)
    {
        for (int i = 0; i < indent; ++i)
            os << "    ";
        return os;
    }

    std::ostream& printIpAddress(std::ostream& os, const ce::nbapi::ip_address& msg, int indent)
    {
        static const size_t IPV6_SIZE = (sizeof(uint8_t) * 16);
        static const size_t IPV4_SIZE = sizeof(uint32_t);
        
        if (msg.has_af())
        {
            ce::nbapi::ip_address::addr_family af = msg.af();
            printIndent(os, indent); os << "af: " << msg.addr_family_Name(af) << "\n";

            if (msg.has_addr())
            {
                const std::string& addrTmp = msg.addr();
                struct sockaddr_in sin;
                struct sockaddr_in6 sin6; 
                socklen_t salen;
                int error = -1;
                char nameInfo[80];
                
                if (af == ce::nbapi::ip_address::ADDR_FAMILY_INET6)
                {
                    memset(&sin6, 0, sizeof(struct sockaddr_in6));
                    sin6.sin6_family = AF_INET6; 
                    memcpy(sin6.sin6_addr.s6_addr, addrTmp.data(), IPV6_SIZE);
                    salen = sizeof(struct sockaddr_in6);
                    error = getnameinfo((struct sockaddr *)&sin6, salen, nameInfo, sizeof(nameInfo),
                                        NULL, 0, NI_NUMERICHOST);
                }
                else
                {
                    memset(&sin, 0, sizeof (struct sockaddr_in));
                    sin.sin_family =  AF_INET;
                    memcpy(&sin.sin_addr.s_addr, addrTmp.data(), IPV4_SIZE);
                    salen = sizeof(struct sockaddr_in);
                    error = getnameinfo((struct sockaddr *)&sin, salen, nameInfo, sizeof(nameInfo),
                                        NULL, 0, NI_NUMERICHOST);
                }

                if (!error)
                    printIndent(os, indent); os << "addr: " << nameInfo << "\n";
            }
        }
        return os;
    }

    std::ostream& printMacAddress(std::ostream& os, const ce::nbapi::mac_address& msg, int indent)
    {
        if (msg.has_addr())
        {
            const std::string& addrTmp = msg.addr();
            if (addrTmp.size() == 6)
            {
                const unsigned char* addrData = (const unsigned char*)addrTmp.data();
                char macAddStr[18];
                sprintf(macAddStr, "%02x:%02x:%02x:%02x:%02x:%02x",
                        addrData[0], addrData[1], addrData[2],
                        addrData[3], addrData[4], addrData[5]);
                printIndent(os, indent); os << "addr: " << macAddStr << "\n";
            }
        }
        return os;
    }

    std::ostream& printMessage(std::ostream& os, const gpb::Message& msg, int indent)
    {   
        const gpb::Descriptor* desc = msg.GetDescriptor();

        try
        {
            if (desc == ce::nbapi::ip_address::descriptor())
                return printIpAddress(os, dynamic_cast<const ce::nbapi::ip_address&>(msg), indent);
            else if (desc == ce::nbapi::mac_address::descriptor())
                return printMacAddress(os, dynamic_cast<const ce::nbapi::mac_address&>(msg), indent);
        }
        catch (const std::bad_cast& e)
        {
            return os;
        }
        
        const gpb::Reflection* refl = msg.GetReflection();
        std::vector<const gpb::FieldDescriptor*> fieldDescList;

        refl->ListFields(msg, &fieldDescList);
        for (size_t i = 0; i < fieldDescList.size(); ++i)
        {
            const gpb::FieldDescriptor* fieldDesc = fieldDescList[i];
            int fieldSize = fieldDesc->is_repeated() ? refl->FieldSize(msg, fieldDesc) : -1;
            int k;
                
            switch (fieldDesc->cpp_type())
            {
                case gpb::FieldDescriptor::CPPTYPE_MESSAGE:
                {
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            printIndent(os, indent); os << fieldDesc->name();
                            os << " {\n";
                            printMessage(os, refl->GetRepeatedMessage(msg, fieldDesc, k), indent+1);
                            printIndent(os, indent); os << "}\n";
                        }
                    }
                    else
                    {
                        printIndent(os, indent); os << fieldDesc->name();
                        os << " {\n";
                        printMessage(os, refl->GetMessage(msg, fieldDesc), indent+1);
                        printIndent(os, indent); os << "}\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_INT32:
                {
                    int32_t tmpInt32;
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpInt32 = refl->GetRepeatedInt32(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << tmpInt32 << "\n";
                        }
                    }
                    else
                    {
                        tmpInt32 = refl->GetInt32(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << tmpInt32 << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_INT64:
                {
                    int64_t tmpInt64;
                    
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpInt64 = refl->GetRepeatedInt64(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << tmpInt64 << "\n";
                        }
                    }
                    else
                    {
                        tmpInt64 = refl->GetInt64(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << tmpInt64 << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_UINT32:
                {
                    uint32_t tmpUInt32;
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpUInt32 = refl->GetRepeatedUInt32(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << tmpUInt32 << "\n";
                        }
                    }
                    else
                    {
                        tmpUInt32 = refl->GetUInt32(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << tmpUInt32 << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_UINT64:
                {
                    uint64_t tmpUInt64;
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpUInt64 = refl->GetRepeatedUInt64(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << tmpUInt64 << "\n";
                        }
                    }
                    else
                    {
                        tmpUInt64 = refl->GetUInt64(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << tmpUInt64 << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_DOUBLE:
                {
                    double tmpDouble;
                    
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpDouble = refl->GetRepeatedDouble(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << tmpDouble << "\n";
                        }
                    }
                    else
                    {
                        tmpDouble = refl->GetDouble(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << tmpDouble << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_FLOAT:
                {
                    float tmpFloat;
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpFloat = refl->GetRepeatedFloat(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << tmpFloat << "\n";
                        }
                    }
                    else
                    {
                        tmpFloat = refl->GetFloat(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << tmpFloat << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_BOOL:
                {
                    bool tmpBool;

                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpBool = refl->GetRepeatedBool(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << (tmpBool ? "true" : "false")  << "\n";
                        }
                    }
                    else
                    {
                        tmpBool = refl->GetBool(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << (tmpBool ? "true" : "false")  << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_ENUM:
                {
                    const gpb::EnumValueDescriptor* enumDesc;
                    
                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            enumDesc = refl->GetRepeatedEnum(msg, fieldDesc, k);
                            printIndent(os, indent); os << fieldDesc->name();
                            os << ": " << enumDesc->name() << "\n";
                        }
                    }
                    else
                    {
                        enumDesc = refl->GetEnum(msg, fieldDesc);
                        printIndent(os, indent); os << fieldDesc->name();
                        os << ": " << enumDesc->name() << "\n";
                    }
                }
                break;
                case gpb::FieldDescriptor::CPPTYPE_STRING:
                {
                    std::string tmpString;

                    if (fieldDesc->is_repeated())
                    {
                        for (k = 0; k < fieldSize; ++k)
                        {
                            tmpString = refl->GetRepeatedStringReference(msg, fieldDesc, k, &tmpString);

                            printIndent(os, indent); os << fieldDesc->name();
                        
                            if (fieldDesc->type() == gpb::FieldDescriptor::TYPE_STRING)
                                os << ": " << tmpString << "\n";
                            else
                            {
                                char* tmpSz = new char[(tmpString.size()*2)+1];
                                const unsigned char* data = (const unsigned char*)tmpString.data();
                                for (size_t j=0; j < tmpString.size(); ++j)
                                    sprintf(&tmpSz[j*2], "%02X", data[j]);
                                os << ": " << tmpSz << "\n";
                                delete[] tmpSz;
                            }
                        }
                    }
                    else
                    {
                        tmpString = refl->GetStringReference(msg, fieldDesc, &tmpString);

                        printIndent(os, indent); os << fieldDesc->name();
                        
                        if (fieldDesc->type() == gpb::FieldDescriptor::TYPE_STRING)
                            os << ": " << tmpString << "\n";
                        else
                        {
                            char* tmpSz = new char[(tmpString.size()*2)+1];
                            const unsigned char* data = (const unsigned char*)tmpString.data();
                            for (size_t j=0; j < tmpString.size(); ++j)
                                sprintf(&tmpSz[j*2], "%02X", data[j]);
                            os << ": " << tmpSz << "\n";
                            delete[] tmpSz;
                        }
                    }
                }
                break;
                default:
                    printIndent(os, indent); os << ": ???\n";
                    break;
            }
        }
        return os;
    }

    std::ostream& operator<<(std::ostream& os, const ce::nbapi::nb_event& ev)
    {
        return printMessage(os, ev, 0);
    }
}

int main(int argc, char* argv[])
{
    g_appName = argv[0];
    std::string endpoint(DEFAULT_ZMQ_ENDPOINT);
    std::string filter(DEFAULT_ZMQ_SUB_FILTER);
    int c;
    bool doBind = false;
    
    while((c = getopt(argc, argv, "hf:e:b")) != -1)
    {
        switch (c)
        {
            case 'f':
                if (optarg && optarg[0])
                    filter.assign(optarg);
                break;
            case 'e':
                if (optarg && optarg[0])
                    endpoint.assign(optarg);
                break;
            case 'b':
                doBind = true;
                break;
            default:
                usage();
                break;
        };
    }

    void* ctx = zmq_ctx_new();
    if (!ctx)
        perror("zmq_ctx_new");
    assert(ctx);
    
    void* sub = zmq_socket(ctx, ZMQ_SUB);
    if (!sub)
        perror("zmq_socket");
    assert(sub);

    if (doBind)
    {
        endpoint.assign("tcp://*:7779");
        printf("Attempting to 'bind' to endpoint: %s\n", endpoint.c_str());
        if (zmq_bind(sub, endpoint.c_str()) != 0)
        {
            perror("zmq_bind");
            assert(0);
        }
    }
    else
    {
        printf("Attempting to 'connect' to endpoint: %s\n", endpoint.c_str());
        if (zmq_connect(sub, endpoint.c_str()) != 0)
        {
            perror("zmq_connect");
            assert(0);
        }
    }
    printf("Connected to endpoint: %s\n", endpoint.c_str());

    if (zmq_setsockopt(sub, ZMQ_SUBSCRIBE, filter.c_str(), filter.size()) != 0)
    {
        perror("zmq_setsockopt");
        assert(0);
    }
    printf("Subscribed to topic: \"%s\"\n", filter.c_str());

    zmq_msg_t zmsg;
    size_t cnt = 1;
    std::string strTopic;
    ce::nbapi::nb_event ev;
    int rc;
    
    while (true)
    {
        bool more = true;
        size_t partNum = 0;
        
        while (more)
        {
            zmq_msg_init(&zmsg);
            rc = zmq_msg_recv(&zmsg, sub, 0);
            more = zmq_msg_more(&zmsg) != 0;
            
            if (rc < 0)
            {
                perror("zmq_msg_recv");
                more = false;
            }
            else
            {
                if (partNum == 0)
                {
                    strTopic.assign(static_cast<const char*>(zmq_msg_data(&zmsg)), zmq_msg_size(&zmsg));
                    printf("[%zu] Recv event with topic \"%s\"\n", cnt++, strTopic.c_str());
                }
                else
                {
                    ev.Clear();
                    if (ev.ParseFromArray(zmq_msg_data(&zmsg), zmq_msg_size(&zmsg)))
                        std::cout << ev << std::endl;
                    else
                        printf("Protobuf failed to parse event\n");
                }
            }
            zmq_msg_close(&zmsg);
            ++partNum;
        }
    }

    std::cout << "Cleaning..." << std::endl;
        
    if (zmq_close(sub) != 0)
        perror("zmq_close");
    
    if (zmq_ctx_destroy(ctx) != 0)
        perror("zmq_close");
    
    return 0;
}
